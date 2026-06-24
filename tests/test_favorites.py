from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from tests.conftest import register_verified_user


async def _make_course(slug: str) -> int:
    async with AsyncSessionLocal() as db:
        course = Course(
            title=slug, slug=slug, type=CourseType.course, status=CourseStatus.active, price=0
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course.id


async def _auth(client: AsyncClient, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    return {"Authorization": f"Bearer {token}"}


async def test_toggle_favors_and_unfavors(client: AsyncClient):
    headers = await _auth(client, "fav1@aiacademy.tj")
    cid = await _make_course("fav-course-1")

    r = await client.post(f"/api/v1/favorites/toggle/{cid}", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "favored"

    r = await client.get("/api/v1/favorites", headers=headers)
    body = r.json()
    assert len(body) == 1
    assert body[0]["course"]["id"] == cid

    r = await client.post(f"/api/v1/favorites/toggle/{cid}", headers=headers)
    assert r.json()["status"] == "unfavored"

    r = await client.get("/api/v1/favorites", headers=headers)
    assert r.json() == []


async def test_delete_by_favorite_id(client: AsyncClient):
    headers = await _auth(client, "fav-del@aiacademy.tj")
    cid = await _make_course("fav-del-course")
    await client.post(f"/api/v1/favorites/toggle/{cid}", headers=headers)
    fav_id = (await client.get("/api/v1/favorites", headers=headers)).json()[0]["id"]

    r = await client.delete(f"/api/v1/favorites/{fav_id}", headers=headers)
    assert r.status_code == 200
    assert (await client.get("/api/v1/favorites", headers=headers)).json() == []


async def test_toggle_404_for_missing_course(client: AsyncClient):
    headers = await _auth(client, "fav2@aiacademy.tj")
    r = await client.post("/api/v1/favorites/toggle/9999", headers=headers)
    assert r.status_code == 404


async def test_toggle_requires_auth(client: AsyncClient):
    cid = await _make_course("fav-course-3")
    r = await client.post(f"/api/v1/favorites/toggle/{cid}")
    assert r.status_code == 401


async def test_delete_scoped_to_owner(client: AsyncClient):
    owner = await _auth(client, "fav-owner@aiacademy.tj")
    other = await _auth(client, "fav-other@aiacademy.tj")
    cid = await _make_course("fav-course-4")
    await client.post(f"/api/v1/favorites/toggle/{cid}", headers=owner)
    fav_id = (await client.get("/api/v1/favorites", headers=owner)).json()[0]["id"]

    # another user cannot delete it, and doesn't see it
    assert (await client.delete(f"/api/v1/favorites/{fav_id}", headers=other)).status_code == 404
    assert (await client.get("/api/v1/favorites", headers=other)).json() == []
