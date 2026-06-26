from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment, EnrollmentSource
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _course(slug: str, creator_id: int | None = None) -> int:
    async with AsyncSessionLocal() as db:
        c = Course(
            title=slug,
            slug=slug,
            type=CourseType.course,
            status=CourseStatus.active,
            price=10,
            creator_id=creator_id,
            teacher_id=creator_id,
        )
        db.add(c)
        await db.commit()
        await db.refresh(c)
        return c.id


async def _enroll(user_id: int, course_id: int) -> None:
    async with AsyncSessionLocal() as db:
        db.add(Enrollment(user_id=user_id, course_id=course_id, source=EnrollmentSource.free))
        await db.commit()


async def _make_teacher(uid: int) -> None:
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()


async def test_dashboard_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/panel/dashboard")
    assert r.status_code == 401


async def test_student_dashboard_counts(client: AsyncClient):
    token, uid = await register_verified_user(client, email="dashstud@aiacademy.tj")
    c1 = await _course("dash-c1")
    await _course("dash-c2")
    await _enroll(uid, c1)

    r = await client.get("/api/v1/panel/dashboard", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["is_instructor"] is False
    assert body["enrolled_count"] == 1
    assert body["purchases_count"] == 0
    assert body["courses_count"] == 0  # students get zero instructor metrics


async def test_instructor_dashboard_has_teaching_metrics(client: AsyncClient):
    token, uid = await register_verified_user(client, email="dashteacher@aiacademy.tj")
    await _make_teacher(uid)
    await _course("dash-owned1", creator_id=uid)
    await _course("dash-owned2", creator_id=uid)

    r = await client.get("/api/v1/panel/dashboard", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["is_instructor"] is True
    assert body["courses_count"] == 2
    assert body["sales_count"] == 0
    assert body["sales_income"] == 0
