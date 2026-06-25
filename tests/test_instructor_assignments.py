from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.assignment import (
    Assignment,
    AssignmentHistory,
    AssignmentHistoryMessage,
    AssignmentHistoryStatus,
    AssignmentStatus,
)
from app.models.course import Course, CourseStatus, CourseType
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


async def _assignment(course_id: int, creator_id: int, pass_grade: int = 50) -> int:
    async with AsyncSessionLocal() as db:
        a = Assignment(
            course_id=course_id,
            creator_id=creator_id,
            title="Homework 1",
            pass_grade=pass_grade,
            status=AssignmentStatus.active,
        )
        db.add(a)
        await db.commit()
        return a.id


async def _history(
    assignment_id: int, instructor_id: int, student_id: int, *, messages: int = 1
) -> int:
    async with AsyncSessionLocal() as db:
        h = AssignmentHistory(
            assignment_id=assignment_id,
            instructor_id=instructor_id,
            student_id=student_id,
            status=AssignmentHistoryStatus.pending,
        )
        db.add(h)
        await db.flush()
        for i in range(messages):
            db.add(
                AssignmentHistoryMessage(
                    assignment_history_id=h.id, sender_id=student_id, message=f"submission {i}"
                )
            )
        await db.commit()
        return h.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_dashboard(client: AsyncClient):
    token, tid = await _teacher(client)
    _, student = await register_verified_user(client, email="stu@aiacademy.tj")
    course_id = await _course(tid)
    a_id = await _assignment(course_id, tid)
    await _history(a_id, tid, student, messages=2)

    r = await client.get("/api/v1/panel/assignments", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["course_assignments_count"] == 1
    assert body["pending_reviews_count"] == 1
    assert body["passed_count"] == 0
    assert len(body["assignments"]) == 1
    assert body["assignments"][0]["histories"][0]["submissions_count"] == 2


async def test_submissions_thread(client: AsyncClient):
    token, tid = await _teacher(client)
    _, student = await register_verified_user(client, email="stu@aiacademy.tj")
    course_id = await _course(tid)
    a_id = await _assignment(course_id, tid)
    await _history(a_id, tid, student, messages=2)

    r = await client.get(f"/api/v1/panel/assignments/{a_id}/submissions", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["student"]["id"] == student
    assert len(body[0]["messages"]) == 2


async def test_grade_pass_and_fail(client: AsyncClient):
    token, tid = await _teacher(client)
    _, student = await register_verified_user(client, email="stu@aiacademy.tj")
    course_id = await _course(tid)
    a_id = await _assignment(course_id, tid, pass_grade=50)
    h_id = await _history(a_id, tid, student)

    r = await client.post(
        f"/api/v1/panel/assignments/histories/{h_id}/rate",
        json={"grade": 80},
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "passed"
    assert r.json()["grade"] == 80

    r2 = await client.post(
        f"/api/v1/panel/assignments/histories/{h_id}/rate",
        json={"grade": 20},
        headers=_auth(token),
    )
    assert r2.json()["status"] == "not_passed"


async def test_grade_foreign_history_404(client: AsyncClient):
    token, tid = await _teacher(client)
    other_token, other_id = await _teacher(client, email="other@aiacademy.tj")
    _, student = await register_verified_user(client, email="stu@aiacademy.tj")
    course_id = await _course(other_id, slug="oc")
    a_id = await _assignment(course_id, other_id)
    h_id = await _history(a_id, other_id, student)

    r = await client.post(
        f"/api/v1/panel/assignments/histories/{h_id}/rate",
        json={"grade": 90},
        headers=_auth(token),  # not the creator
    )
    assert r.status_code == 404


async def test_requires_teacher(client: AsyncClient):
    token, _ = await register_verified_user(client)
    assert (await client.get("/api/v1/panel/assignments", headers=_auth(token))).status_code == 403
