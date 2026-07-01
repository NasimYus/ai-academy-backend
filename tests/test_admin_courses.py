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


async def _typed_course(slug: str, ctype: CourseType, status: CourseStatus, duration: int) -> int:
    async with AsyncSessionLocal() as db:
        c = Course(title=slug, slug=slug, type=ctype, status=status, price=10, duration=duration)
        db.add(c)
        await db.commit()
        await db.refresh(c)
        return c.id


async def test_manage_list_stats_and_type_filter(client: AsyncClient):
    token = await _admin(client, email="manageadmin@aiacademy.tj")
    await _typed_course("m-course-1", CourseType.course, CourseStatus.active, 120)
    await _typed_course("m-course-2", CourseType.course, CourseStatus.pending, 60)
    await _typed_course("m-webinar-1", CourseType.webinar, CourseStatus.active, 45)

    courses = (
        await client.get("/api/v1/admin/courses/manage?type=course", headers=_auth(token))
    ).json()
    assert courses["total_courses"] == 2
    assert courses["total_pending"] == 1
    assert courses["total_duration"] == 180
    assert courses["total"] == 2
    assert {c["type"] for c in courses["courses"]} == {"course"}
    assert all("income" in c and "students_count" in c for c in courses["courses"])

    webinars = (
        await client.get("/api/v1/admin/courses/manage?type=webinar", headers=_auth(token))
    ).json()
    assert webinars["total_courses"] == 1
    assert webinars["courses"][0]["type"] == "webinar"


async def test_manage_search_and_status_filter(client: AsyncClient):
    token = await _admin(client, email="manage2@aiacademy.tj")
    await _typed_course("Python basics", CourseType.course, CourseStatus.active, 10)
    await _typed_course("Java basics", CourseType.course, CourseStatus.pending, 10)

    found = (
        await client.get(
            "/api/v1/admin/courses/manage?type=course&search=python", headers=_auth(token)
        )
    ).json()
    assert found["total"] == 1
    assert found["courses"][0]["title"] == "Python basics"

    pending = (
        await client.get(
            "/api/v1/admin/courses/manage?type=course&status=pending", headers=_auth(token)
        )
    ).json()
    assert pending["total"] == 1
    assert pending["courses"][0]["status"] == "pending"


async def test_delete_course(client: AsyncClient):
    token = await _admin(client, email="deladmin@aiacademy.tj")
    course_id = await _course("c-del", CourseStatus.active)
    r = await client.delete(f"/api/v1/admin/courses/{course_id}", headers=_auth(token))
    assert r.status_code == 204
    async with AsyncSessionLocal() as db:
        assert await db.get(Course, course_id) is None


async def test_live_sessions_empty(client: AsyncClient):
    token = await _admin(client, email="liveadmin@aiacademy.tj")
    body = (await client.get("/api/v1/admin/courses/live-sessions", headers=_auth(token))).json()
    assert body["total"] == 0
    assert body["sessions"] == []
