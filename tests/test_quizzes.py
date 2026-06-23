from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.quiz import (
    QuestionType,
    Quiz,
    QuizQuestion,
    QuizQuestionAnswer,
    QuizStatus,
)
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _seed_quiz(
    *, pass_mark: int = 15, attempt: int | None = None, descriptive: bool = False
) -> dict:
    """Course (free) + a teacher-owned active quiz with two multiple-choice
    questions (grade 10 each). Returns ids needed by tests."""
    async with AsyncSessionLocal() as db:
        teacher = User(
            full_name="Teacher",
            email="teacher@aiacademy.tj",
            password="x",
            role_id=4,
            role_name=Role.TEACHER,
        )
        db.add(teacher)
        await db.flush()

        course = Course(
            title="Quiz Course",
            slug="quiz-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add(course)
        await db.flush()

        quiz = Quiz(
            course_id=course.id,
            creator_id=teacher.id,
            title="Sample Quiz",
            time=0,
            attempt=attempt,
            pass_mark=pass_mark,
            certificate=False,
            status=QuizStatus.active,
        )
        db.add(quiz)
        await db.flush()

        ids: dict = {"course_id": course.id, "quiz_id": quiz.id, "teacher_id": teacher.id}

        q1 = QuizQuestion(
            quiz_id=quiz.id,
            creator_id=teacher.id,
            title="2 + 2 = ?",
            grade=10,
            type=QuestionType.multiple,
            order=1,
        )
        db.add(q1)
        await db.flush()
        a1 = QuizQuestionAnswer(question_id=q1.id, creator_id=teacher.id, title="4", correct=True)
        a2 = QuizQuestionAnswer(question_id=q1.id, creator_id=teacher.id, title="5", correct=False)
        db.add_all([a1, a2])
        await db.flush()
        ids.update(q1=q1.id, q1_correct=a1.id, q1_wrong=a2.id)

        if descriptive:
            qd = QuizQuestion(
                quiz_id=quiz.id,
                creator_id=teacher.id,
                title="Explain.",
                grade=10,
                type=QuestionType.descriptive,
                correct="the expected essay",
                order=2,
            )
            db.add(qd)
            await db.flush()
            ids["qd"] = qd.id
        else:
            q2 = QuizQuestion(
                quiz_id=quiz.id,
                creator_id=teacher.id,
                title="3 + 3 = ?",
                grade=10,
                type=QuestionType.multiple,
                order=2,
            )
            db.add(q2)
            await db.flush()
            a3 = QuizQuestionAnswer(
                question_id=q2.id, creator_id=teacher.id, title="6", correct=True
            )
            a4 = QuizQuestionAnswer(
                question_id=q2.id, creator_id=teacher.id, title="7", correct=False
            )
            db.add_all([a3, a4])
            await db.flush()
            ids.update(q2=q2.id, q2_correct=a3.id, q2_wrong=a4.id)

        await db.commit()
        return ids


async def _enrolled_headers(client: AsyncClient, course_id: int, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(f"/api/v1/panel/courses/{course_id}/free", headers=headers)
    return headers


async def test_show_quiz_anonymous(client: AsyncClient):
    ids = await _seed_quiz()
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Sample Quiz"
    assert body["question_count"] == 2
    assert body["total_mark"] == 20
    assert len(body["questions"]) == 2
    # anonymous -> auth-scoped fields are null
    assert body["auth_status"] is None
    assert body["auth_can_start"] is None


async def test_show_quiz_404(client: AsyncClient):
    r = await client.get("/api/v1/quizzes/999")
    assert r.status_code == 404


async def test_start_requires_auth(client: AsyncClient):
    ids = await _seed_quiz()
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/start")
    assert r.status_code == 401


async def test_start_requires_access(client: AsyncClient):
    ids = await _seed_quiz()
    token, _ = await register_verified_user(client, "noaccess@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/start", headers=headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "not_purchased"


async def test_full_pass_flow(client: AsyncClient):
    ids = await _seed_quiz(pass_mark=15)
    headers = await _enrolled_headers(client, ids["course_id"], "pass@aiacademy.tj")

    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/start", headers=headers)
    assert r.status_code == 200
    start = r.json()
    assert start["attempt_number"] == 1
    # details are computed after the waiting attempt is created (legacy parity)
    assert start["quiz"]["auth_status"] == "waiting"
    result_id = start["quiz_result_id"]

    r = await client.post(
        f"/api/v1/quizzes/{ids['quiz_id']}/store-result",
        headers=headers,
        json={
            "quiz_result_id": result_id,
            "answer_sheet": [
                {"question_id": ids["q1"], "answer": ids["q1_correct"]},
                {"question_id": ids["q2"], "answer": ids["q2_correct"]},
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "passed"
    assert body["user_grade"] == 20

    # result_by_quiz returns the passed attempt
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/result", headers=headers)
    assert r.json()["status"] == "passed"

    # status endpoint returns the same result
    r = await client.get(f"/api/v1/quizzes/results/{result_id}/status", headers=headers)
    assert r.json()["id"] == result_id


async def test_fail_flow(client: AsyncClient):
    ids = await _seed_quiz(pass_mark=15)
    headers = await _enrolled_headers(client, ids["course_id"], "fail@aiacademy.tj")
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/start", headers=headers)
    result_id = r.json()["quiz_result_id"]

    r = await client.post(
        f"/api/v1/quizzes/{ids['quiz_id']}/store-result",
        headers=headers,
        json={
            "quiz_result_id": result_id,
            "answer_sheet": [
                {"question_id": ids["q1"], "answer": ids["q1_wrong"]},
                {"question_id": ids["q2"], "answer": ids["q2_wrong"]},
            ],
        },
    )
    body = r.json()
    assert body["status"] == "failed"
    assert body["user_grade"] == 0


async def test_descriptive_goes_waiting(client: AsyncClient):
    ids = await _seed_quiz(pass_mark=15, descriptive=True)
    headers = await _enrolled_headers(client, ids["course_id"], "desc@aiacademy.tj")
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/start", headers=headers)
    result_id = r.json()["quiz_result_id"]

    r = await client.post(
        f"/api/v1/quizzes/{ids['quiz_id']}/store-result",
        headers=headers,
        json={
            "quiz_result_id": result_id,
            "answer_sheet": [
                {"question_id": ids["q1"], "answer": ids["q1_correct"]},
                {"question_id": ids["qd"], "answer": "my essay answer"},
            ],
        },
    )
    body = r.json()
    assert body["status"] == "waiting"
    assert body["reviewable"] is True


async def test_max_attempt_blocks_start(client: AsyncClient):
    ids = await _seed_quiz(pass_mark=15, attempt=1)
    headers = await _enrolled_headers(client, ids["course_id"], "max@aiacademy.tj")

    # attempt #1 (fail so 'passed' doesn't short-circuit)
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/start", headers=headers)
    result_id = r.json()["quiz_result_id"]
    await client.post(
        f"/api/v1/quizzes/{ids['quiz_id']}/store-result",
        headers=headers,
        json={
            "quiz_result_id": result_id,
            "answer_sheet": [{"question_id": ids["q1"], "answer": ids["q1_wrong"]}],
        },
    )

    # attempt #2 blocked
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/start", headers=headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "max_attempt"


async def test_store_result_rejects_foreign_question(client: AsyncClient):
    ids = await _seed_quiz()
    headers = await _enrolled_headers(client, ids["course_id"], "foreign@aiacademy.tj")
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/start", headers=headers)
    result_id = r.json()["quiz_result_id"]

    r = await client.post(
        f"/api/v1/quizzes/{ids['quiz_id']}/store-result",
        headers=headers,
        json={
            "quiz_result_id": result_id,
            "answer_sheet": [{"question_id": 99999, "answer": 1}],
        },
    )
    assert r.status_code == 422


async def test_list_course_quizzes(client: AsyncClient):
    ids = await _seed_quiz()
    r = await client.get(f"/api/v1/courses/{ids['course_id']}/quizzes")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["id"] == ids["quiz_id"]
