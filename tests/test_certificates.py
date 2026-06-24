from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.quiz import Quiz, QuizResult, QuizStatus, ResultStatus
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _seed_quiz(*, certificate: bool = True) -> dict:
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
            title="Cert Course",
            slug="cert-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add(course)
        await db.flush()
        quiz = Quiz(
            course_id=course.id,
            creator_id=teacher.id,
            title="Final Exam",
            time=0,
            pass_mark=5,
            certificate=certificate,
            status=QuizStatus.active,
            total_mark=10,
        )
        db.add(quiz)
        await db.commit()
        return {"course_id": course.id, "quiz_id": quiz.id}


async def _seed_passed_result(quiz_id: int, user_id: int, grade: int = 10) -> int:
    async with AsyncSessionLocal() as db:
        result = QuizResult(
            quiz_id=quiz_id, user_id=user_id, user_grade=grade, status=ResultStatus.passed
        )
        db.add(result)
        await db.commit()
        return result.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_show_issues_and_renders_pdf(client: AsyncClient):
    ids = await _seed_quiz()
    token, user_id = await register_verified_user(client, email="student@aiacademy.tj")
    result_id = await _seed_passed_result(ids["quiz_id"], user_id)

    r = await client.get(f"/api/v1/panel/quizzes/results/{result_id}/show", headers=_auth(token))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


async def test_achievements_list_with_certificate(client: AsyncClient):
    ids = await _seed_quiz()
    token, user_id = await register_verified_user(client, email="student@aiacademy.tj")
    result_id = await _seed_passed_result(ids["quiz_id"], user_id)
    # render once so the certificate row exists
    await client.get(f"/api/v1/panel/quizzes/results/{result_id}/show", headers=_auth(token))

    r = await client.get("/api/v1/panel/certificates/achievements", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["quiz_title"] == "Final Exam"
    assert body[0]["certificate"] is not None
    assert body[0]["certificate"]["file"].endswith(".pdf")


async def test_validation(client: AsyncClient):
    ids = await _seed_quiz()
    token, user_id = await register_verified_user(client, email="student@aiacademy.tj")
    result_id = await _seed_passed_result(ids["quiz_id"], user_id)
    await client.get(f"/api/v1/panel/quizzes/results/{result_id}/show", headers=_auth(token))

    r = await client.get("/api/v1/certificate_validation", params={"certificate_id": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is True
    assert body["certificate"]["quiz_title"] == "Final Exam"
    assert body["certificate"]["student_name"] == "Test User"

    bad = await client.get("/api/v1/certificate_validation", params={"certificate_id": 999})
    assert bad.status_code == 200
    assert bad.json()["is_valid"] is False


async def test_show_requires_passed_result(client: AsyncClient):
    await _seed_quiz()
    token, _ = await register_verified_user(client, email="student@aiacademy.tj")
    r = await client.get("/api/v1/panel/quizzes/results/999/show", headers=_auth(token))
    assert r.status_code == 404


async def test_no_certificate_when_quiz_flag_off(client: AsyncClient):
    ids = await _seed_quiz(certificate=False)
    token, user_id = await register_verified_user(client, email="student@aiacademy.tj")
    result_id = await _seed_passed_result(ids["quiz_id"], user_id)
    r = await client.get(f"/api/v1/panel/quizzes/results/{result_id}/show", headers=_auth(token))
    assert r.status_code == 404
