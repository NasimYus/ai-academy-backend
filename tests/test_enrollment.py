from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from tests.conftest import register_verified_user


async def _make_course(slug: str, price: float) -> int:
    async with AsyncSessionLocal() as db:
        course = Course(
            title=slug, slug=slug, type=CourseType.course, status=CourseStatus.active, price=price
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course.id


async def test_free_enroll_grants_access(client: AsyncClient):
    token, _ = await register_verified_user(client, "e@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    course_id = await _make_course("free-course", 0)

    r = await client.post(f"/api/v1/panel/courses/{course_id}/free", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "enrolled"

    # idempotent
    r = await client.post(f"/api/v1/panel/courses/{course_id}/free", headers=headers)
    assert r.status_code == 200

    # detail now reports access for this user
    r = await client.get("/api/v1/courses/free-course", headers=headers)
    assert r.json()["auth_has_bought"] is True
    assert r.json()["auth"] is True


async def test_free_enroll_rejects_paid_course(client: AsyncClient):
    token, _ = await register_verified_user(client, "e2@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    course_id = await _make_course("paid-course", 100)

    r = await client.post(f"/api/v1/panel/courses/{course_id}/free", headers=headers)
    assert r.status_code == 400
    assert r.json()["detail"] == "not_free"


async def test_free_enroll_requires_auth(client: AsyncClient):
    course_id = await _make_course("free-course-2", 0)
    r = await client.post(f"/api/v1/panel/courses/{course_id}/free")
    assert r.status_code == 401


async def test_detail_anonymous_has_no_access(client: AsyncClient):
    await _make_course("anon-course", 0)
    r = await client.get("/api/v1/courses/anon-course")
    assert r.json()["auth"] is False
    assert r.json()["auth_has_bought"] is False
