from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.noticeboard import CourseNoticeboard, NoticeboardColor
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _seed() -> tuple[int, int]:
    """Course + a teacher creator + two noticeboards. Returns (course_id, board_id)."""
    async with AsyncSessionLocal() as db:
        teacher = User(
            full_name="Teacher",
            email="nb-teacher@aiacademy.tj",
            password="x",
            role_id=4,
            role_name=Role.TEACHER,
        )
        db.add(teacher)
        await db.flush()
        course = Course(
            title="NB Course",
            slug="nb-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add(course)
        await db.flush()
        b1 = CourseNoticeboard(
            creator_id=teacher.id,
            course_id=course.id,
            color=NoticeboardColor.info,
            title="First",
            message="hello",
        )
        b2 = CourseNoticeboard(
            creator_id=teacher.id,
            course_id=course.id,
            color=NoticeboardColor.warning,
            title="Second",
            message="careful",
        )
        db.add_all([b1, b2])
        await db.commit()
        return course.id, b2.id


async def test_list_returns_boards_newest_first(client: AsyncClient):
    course_id, latest_id = await _seed()
    token, _ = await register_verified_user(client, "nb1@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/api/v1/courses/{course_id}/noticeboards", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["id"] == latest_id  # newest first
    assert body[0]["title"] == "Second"
    assert body[0]["color"] == "warning"
    assert body[0]["icon"] == "danger"  # warning -> danger icon
    assert body[1]["icon"] == "info-circle"  # info -> info-circle
    assert body[0]["creator"]["full_name"] == "Teacher"


async def test_list_requires_auth(client: AsyncClient):
    course_id, _ = await _seed()
    r = await client.get(f"/api/v1/courses/{course_id}/noticeboards")
    assert r.status_code == 401


async def test_list_course_404(client: AsyncClient):
    token, _ = await register_verified_user(client, "nb2@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/v1/courses/999/noticeboards", headers=headers)
    assert r.status_code == 404
