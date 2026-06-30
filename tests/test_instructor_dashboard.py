from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment, EnrollmentSource
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _make_teacher(uid: int) -> None:
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()


async def test_instructor_dashboard_requires_teacher(client: AsyncClient):
    token, _ = await register_verified_user(client, email="id-student@aiacademy.tj")
    # plain student is below teacher level
    assert (
        await client.get("/api/v1/panel/instructor-dashboard", headers=_auth(token))
    ).status_code == 403


async def test_instructor_dashboard_counts_and_cards(client: AsyncClient):
    token, uid = await register_verified_user(client, email="id-teacher@aiacademy.tj")
    await _make_teacher(uid)
    student_token, student_uid = await register_verified_user(client, email="id-pupil@aiacademy.tj")

    async with AsyncSessionLocal() as db:
        live = Course(
            title="Live AI",
            slug="id-live",
            type=CourseType.webinar,
            status=CourseStatus.active,
            price=10,
            creator_id=uid,
            teacher_id=uid,
        )
        video = Course(
            title="Video ML",
            slug="id-video",
            type=CourseType.course,
            status=CourseStatus.active,
            price=10,
            creator_id=uid,
            teacher_id=uid,
        )
        db.add_all([live, video])
        await db.commit()
        await db.refresh(video)
        db.add(Enrollment(user_id=student_uid, course_id=video.id, source=EnrollmentSource.free))
        await db.commit()
        video_id = video.id

    body = (await client.get("/api/v1/panel/instructor-dashboard", headers=_auth(token))).json()
    assert body["courses_count"] == 2
    assert body["live_courses"] == 1
    assert body["video_courses"] == 1
    assert body["products_count"] == 0
    assert len(body["manage_courses"]) == 2
    video_card = next(c for c in body["manage_courses"] if c["id"] == video_id)
    assert video_card["students_count"] == 1
