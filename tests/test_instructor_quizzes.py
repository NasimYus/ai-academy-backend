from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.course import Course, CourseStatus, CourseType
from app.models.quiz import Quiz, QuizResult, QuizStatus, ResultStatus
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _teacher(client: AsyncClient, email: str = "teacher@aiacademy.tj") -> tuple[str, int]:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return token, uid


async def _course(teacher_id: int, slug: str = "c1") -> int:
    async with AsyncSessionLocal() as db:
        c = Course(
            title="Course",
            slug=slug,
            type=CourseType.course,
            status=CourseStatus.active,
            price=10,
            teacher_id=teacher_id,
            creator_id=teacher_id,
        )
        db.add(c)
        await db.commit()
        return c.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _quiz_payload(course_id: int, **over) -> dict:
    base = {"title": "Quiz 1", "course_id": course_id, "pass_mark": 50, "active": True}
    base.update(over)
    return base


async def test_create_quiz(client: AsyncClient):
    token, uid = await _teacher(client)
    course_id = await _course(uid)
    r = await client.post(
        "/api/v1/panel/quizzes", json=_quiz_payload(course_id), headers=_auth(token)
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Quiz 1"
    assert body["status"] == "active"
    assert body["course_id"] == course_id


async def test_create_quiz_inactive_when_not_active(client: AsyncClient):
    token, uid = await _teacher(client)
    course_id = await _course(uid)
    r = await client.post(
        "/api/v1/panel/quizzes",
        json=_quiz_payload(course_id, active=False),
        headers=_auth(token),
    )
    assert r.json()["status"] == "inactive"


async def test_create_quiz_foreign_course_404(client: AsyncClient):
    token, _ = await _teacher(client)
    _, other_id = await _teacher(client, email="other@aiacademy.tj")
    foreign_course = await _course(other_id, slug="foreign")
    r = await client.post(
        "/api/v1/panel/quizzes", json=_quiz_payload(foreign_course), headers=_auth(token)
    )
    assert r.status_code == 404


async def test_non_teacher_forbidden(client: AsyncClient):
    token, uid = await register_verified_user(client)  # plain user
    course_id = await _course(uid)
    r = await client.post(
        "/api/v1/panel/quizzes", json=_quiz_payload(course_id), headers=_auth(token)
    )
    assert r.status_code == 403


async def test_update_quiz(client: AsyncClient):
    token, uid = await _teacher(client)
    course_id = await _course(uid)
    created = (
        await client.post(
            "/api/v1/panel/quizzes", json=_quiz_payload(course_id), headers=_auth(token)
        )
    ).json()
    r = await client.put(
        f"/api/v1/panel/quizzes/{created['id']}",
        json=_quiz_payload(course_id, title="Renamed", pass_mark=70, active=False),
        headers=_auth(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Renamed"
    assert body["pass_mark"] == 70
    assert body["status"] == "inactive"


async def test_update_foreign_quiz_404(client: AsyncClient):
    token, uid = await _teacher(client)
    course_id = await _course(uid)
    other_token, other_id = await _teacher(client, email="other@aiacademy.tj")
    other_course = await _course(other_id, slug="oc")
    foreign = (
        await client.post(
            "/api/v1/panel/quizzes",
            json=_quiz_payload(other_course),
            headers=_auth(other_token),
        )
    ).json()
    r = await client.put(
        f"/api/v1/panel/quizzes/{foreign['id']}",
        json=_quiz_payload(course_id, title="hijack"),
        headers=_auth(token),
    )
    assert r.status_code == 404


async def test_delete_quiz(client: AsyncClient):
    token, uid = await _teacher(client)
    course_id = await _course(uid)
    created = (
        await client.post(
            "/api/v1/panel/quizzes", json=_quiz_payload(course_id), headers=_auth(token)
        )
    ).json()
    r = await client.delete(f"/api/v1/panel/quizzes/{created['id']}", headers=_auth(token))
    assert r.status_code == 204
    # gone
    r2 = await client.delete(f"/api/v1/panel/quizzes/{created['id']}", headers=_auth(token))
    assert r2.status_code == 404


async def test_results_dashboard(client: AsyncClient):
    token, uid = await _teacher(client)
    course_id = await _course(uid)
    student_token, student_id = await register_verified_user(client, email="stu@aiacademy.tj")

    async with AsyncSessionLocal() as db:
        quiz = Quiz(
            title="Graded",
            course_id=course_id,
            creator_id=uid,
            pass_mark=50,
            time=0,
            status=QuizStatus.active,
        )
        db.add(quiz)
        await db.flush()
        db.add_all(
            [
                QuizResult(
                    quiz_id=quiz.id, user_id=student_id, user_grade=80, status=ResultStatus.passed
                ),
                QuizResult(
                    quiz_id=quiz.id, user_id=student_id, user_grade=20, status=ResultStatus.failed
                ),
            ]
        )
        await db.commit()

    r = await client.get("/api/v1/panel/quizzes/list", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["quiz_results_count"] == 2
    assert body["passed_count"] == 1
    assert body["success_rate"] == 50
    assert body["avg_grade"] == 50.0
    assert len(body["quizzes"]) == 1
    assert len(body["results"]) == 2
    assert body["results"][0]["user"]["full_name"] is not None


async def test_results_requires_teacher(client: AsyncClient):
    token, _ = await register_verified_user(client)
    r = await client.get("/api/v1/panel/quizzes/list", headers=_auth(token))
    assert r.status_code == 403
