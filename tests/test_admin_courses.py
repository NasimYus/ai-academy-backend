from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _admin(client: AsyncClient, email: str = "courseadmin@aiacademy.tj") -> str:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.ADMIN
        user.role_id = 2
        await db.commit()
    return token


async def _course(slug: str, course_status: CourseStatus) -> int:
    async with AsyncSessionLocal() as db:
        c = Course(title=slug, slug=slug, type=CourseType.course, status=course_status, price=10)
        db.add(c)
        await db.commit()
        await db.refresh(c)
        return c.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_non_admin_forbidden(client: AsyncClient):
    token, _ = await register_verified_user(client)
    r = await client.get("/api/v1/admin/courses", headers=_auth(token))
    assert r.status_code == 403


async def test_list_and_pending_count(client: AsyncClient):
    token = await _admin(client)
    await _course("c-active", CourseStatus.active)
    await _course("c-pending1", CourseStatus.pending)
    await _course("c-pending2", CourseStatus.pending)

    full = (await client.get("/api/v1/admin/courses", headers=_auth(token))).json()
    assert full["count"] == 3
    assert full["pending_count"] == 2

    only_pending = (
        await client.get("/api/v1/admin/courses?status=pending", headers=_auth(token))
    ).json()
    assert only_pending["count"] == 2
    assert all(c["status"] == "pending" for c in only_pending["courses"])


async def test_approve_reject_unpublish(client: AsyncClient):
    token = await _admin(client)
    course_id = await _course("c-moderate", CourseStatus.pending)

    approved = await client.post(f"/api/v1/admin/courses/{course_id}/approve", headers=_auth(token))
    assert approved.status_code == 200
    assert approved.json()["status"] == "active"

    unpublished = await client.post(
        f"/api/v1/admin/courses/{course_id}/unpublish", headers=_auth(token)
    )
    assert unpublished.json()["status"] == "pending"

    rejected = await client.post(f"/api/v1/admin/courses/{course_id}/reject", headers=_auth(token))
    assert rejected.json()["status"] == "inactive"


async def test_moderate_missing_course_404(client: AsyncClient):
    token = await _admin(client)
    r = await client.post("/api/v1/admin/courses/999/approve", headers=_auth(token))
    assert r.status_code == 404
