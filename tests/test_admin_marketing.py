from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.featured_course import FeaturedCourse, FeaturedPage, FeaturedStatus
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _make_admin(uid: int) -> None:
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.ADMIN
        await db.commit()


async def test_admin_marketing_requires_admin(client: AsyncClient):
    token, _ = await register_verified_user(client, email="mk-student@aiacademy.tj")
    assert (await client.get("/api/v1/admin/marketing", headers=_auth(token))).status_code == 403


async def test_admin_marketing_shape_and_counts(client: AsyncClient):
    token, uid = await register_verified_user(client, email="mk-admin@aiacademy.tj")
    await _make_admin(uid)

    async with AsyncSessionLocal() as db:
        course = Course(
            title="Active course",
            slug="mk-active",
            type=CourseType.course,
            status=CourseStatus.active,
            price=10,
            creator_id=uid,
            teacher_id=uid,
        )
        db.add(course)
        await db.flush()
        db.add(
            FeaturedCourse(
                course_id=course.id, page=FeaturedPage.home, status=FeaturedStatus.publish
            )
        )
        await db.commit()

    body = (await client.get("/api/v1/admin/marketing", headers=_auth(token))).json()

    # counters
    assert body["featured_classes"] == 1
    assert body["active_discounts"] == 0
    # the admin never purchased anything → counted among users-without-purchases
    assert body["users_without_purchases"] >= 1

    # classes statistics: one active `course` → 100% on the course label, 0% others
    stats = dict(
        zip(
            body["classes_statistics"]["labels"],
            body["classes_statistics"]["data"],
            strict=True,
        )
    )
    assert stats["course"] == 100
    assert stats["webinar"] == 0
    assert stats["text_lesson"] == 0

    # net-profit charts + stats shape
    assert len(body["net_profit_chart_year"]["labels"]) == 12
    assert len(body["net_profit_chart_month"]["labels"]) >= 28
    assert set(body["net_profit_stats"].keys()) == {"today", "week", "month", "year"}

    # tables present (empty on a fresh DB — no sales)
    assert body["top_selling_classes"] == []
    assert body["most_active_students"] == []
