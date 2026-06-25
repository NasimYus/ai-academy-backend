from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.content import Chapter, ChapterStatus
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment, EnrollmentSource
from app.models.review import CourseReview, ReviewStatus
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


async def _seed_course(creator_id: int) -> int:
    async with AsyncSessionLocal() as db:
        student = User(
            full_name="S", email="s@aiacademy.tj", password="x", role_id=1, role_name=Role.USER
        )
        db.add(student)
        await db.flush()
        course = Course(
            title="Stats Course",
            slug="stats-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=100,
            creator_id=creator_id,
            teacher_id=creator_id,
        )
        db.add(course)
        await db.flush()
        db.add_all(
            [
                Enrollment(user_id=student.id, course_id=course.id, source=EnrollmentSource.free),
                CourseReview(
                    course_id=course.id, user_id=student.id, rates=5, status=ReviewStatus.active
                ),
                Chapter(course_id=course.id, title="Ch1", order=1, status=ChapterStatus.active),
            ]
        )
        await db.commit()
        return course.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_statistics_owned_course(client: AsyncClient):
    token, uid = await _teacher(client)
    course_id = await _seed_course(uid)
    r = await client.get(f"/api/v1/panel/webinar/{course_id}/statistic", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["students_count"] == 1
    assert body["reviews_count"] == 1
    assert body["rate"] == 5
    assert body["chapters_count"] == 1
    assert body["sales_count"] == 0
    assert body["quizzes_count"] == 0


async def test_statistics_requires_teacher(client: AsyncClient):
    owner_token, uid = await _teacher(client)
    course_id = await _seed_course(uid)
    plain_token, _ = await register_verified_user(client, email="plain@aiacademy.tj")
    r = await client.get(f"/api/v1/panel/webinar/{course_id}/statistic", headers=_auth(plain_token))
    assert r.status_code == 403


async def test_statistics_not_owner_404(client: AsyncClient):
    owner_token, uid = await _teacher(client, email="owner@aiacademy.tj")
    course_id = await _seed_course(uid)
    other_token, _ = await _teacher(client, email="other@aiacademy.tj")
    r = await client.get(f"/api/v1/panel/webinar/{course_id}/statistic", headers=_auth(other_token))
    assert r.status_code == 404
