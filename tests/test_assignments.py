from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.assignment import Assignment, AssignmentStatus
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment, EnrollmentSource
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _seed(*, attempts: int | None = None) -> dict:
    """Teacher + free active course + one active assignment (total grade 100)."""
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
            title="Assign Course",
            slug="assign-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add(course)
        await db.flush()

        assignment = Assignment(
            course_id=course.id,
            creator_id=teacher.id,
            title="Essay",
            description="Write an essay",
            grade=100,
            pass_grade=50,
            attempts=attempts,
            status=AssignmentStatus.active,
        )
        db.add(assignment)
        await db.commit()
        return {
            "course_id": course.id,
            "assignment_id": assignment.id,
            "teacher_id": teacher.id,
        }


async def _enroll(user_id: int, course_id: int) -> None:
    async with AsyncSessionLocal() as db:
        db.add(Enrollment(user_id=user_id, course_id=course_id, source=EnrollmentSource.free))
        await db.commit()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_show_and_list_assignment(client: AsyncClient):
    ids = await _seed()
    r = await client.get(f"/api/v1/assignments/{ids['assignment_id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Essay"
    assert body["total_grade"] == 100
    assert body["content_type"] == "assignment"

    r = await client.get(f"/api/v1/courses/{ids['course_id']}/assignments")
    assert r.status_code == 200
    assert [a["id"] for a in r.json()] == [ids["assignment_id"]]


async def test_submit_creates_history_and_message(client: AsyncClient):
    ids = await _seed(attempts=2)
    token, user_id = await register_verified_user(client, email="student@aiacademy.tj")
    await _enroll(user_id, ids["course_id"])

    r = await client.post(
        f"/api/v1/assignments/{ids['assignment_id']}/messages",
        data={"message": "My first submission", "file_title": "essay.pdf"},
        headers=_auth(token),
    )
    assert r.status_code == 200
    msg = r.json()
    assert msg["message"] == "My first submission"
    assert msg["sender"]["id"] == user_id
    assert msg["supporter"] is None

    # messages thread now has the submission
    r = await client.get(
        f"/api/v1/assignments/{ids['assignment_id']}/messages", headers=_auth(token)
    )
    assert r.status_code == 200
    assert len(r.json()) == 1

    # my_assignments reflects pending status + one used attempt
    r = await client.get("/api/v1/panel/my_assignments", headers=_auth(token))
    assert r.status_code == 200
    history = r.json()[0]
    assert history["user_status"] == "pending"
    assert history["used_attempts_count"] == 1
    assert history["can_send_message"] is True


async def test_submit_requires_access(client: AsyncClient):
    ids = await _seed()
    token, _ = await register_verified_user(client, email="outsider@aiacademy.tj")
    r = await client.post(
        f"/api/v1/assignments/{ids['assignment_id']}/messages",
        data={"message": "let me in"},
        headers=_auth(token),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "not_purchased"


async def test_attempts_exhausted(client: AsyncClient):
    ids = await _seed(attempts=1)
    token, user_id = await register_verified_user(client, email="student@aiacademy.tj")
    await _enroll(user_id, ids["course_id"])

    first = await client.post(
        f"/api/v1/assignments/{ids['assignment_id']}/messages",
        data={"message": "attempt one"},
        headers=_auth(token),
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/assignments/{ids['assignment_id']}/messages",
        data={"message": "attempt two"},
        headers=_auth(token),
    )
    assert second.status_code == 401


async def test_my_assignment_not_submitted_is_404(client: AsyncClient):
    ids = await _seed()
    token, user_id = await register_verified_user(client, email="student@aiacademy.tj")
    await _enroll(user_id, ids["course_id"])
    r = await client.get(
        f"/api/v1/panel/my_assignments/{ids['assignment_id']}", headers=_auth(token)
    )
    assert r.status_code == 404
