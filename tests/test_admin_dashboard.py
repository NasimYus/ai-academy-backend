from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.comment import Comment, CommentStatus
from app.models.course import Course, CourseStatus, CourseType
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


async def test_admin_dashboard_requires_admin(client: AsyncClient):
    token, _ = await register_verified_user(client, email="ad-student@aiacademy.tj")
    assert (await client.get("/api/v1/admin/dashboard", headers=_auth(token))).status_code == 403


async def test_admin_dashboard_shape_and_counts(client: AsyncClient):
    token, uid = await register_verified_user(client, email="ad-admin@aiacademy.tj")
    await _make_admin(uid)

    async with AsyncSessionLocal() as db:
        db.add(
            Course(
                title="Pending course",
                slug="ad-pending",
                type=CourseType.course,
                status=CourseStatus.pending,
                price=10,
                creator_id=uid,
                teacher_id=uid,
            )
        )
        db.add(Comment(user_id=uid, course_id=None, comment="Hi", status=CommentStatus.new))
        await db.commit()

    body = (await client.get("/api/v1/admin/dashboard", headers=_auth(token))).json()
    assert body["pending_reviews"] == 1
    assert body["new_comments"] == 1
    assert len(body["sales_chart_year"]["labels"]) == 12
    assert len(body["users_chart"]["labels"]) >= 28
    assert set(body["sales_stats"].keys()) == {"today", "week", "month", "year"}
    assert body["daily_sales_by_type"]["total"] == 0
