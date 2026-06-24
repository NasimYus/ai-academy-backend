from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from tests.conftest import register_verified_user


async def _make_course() -> int:
    async with AsyncSessionLocal() as db:
        course = Course(
            title="Notes Course",
            slug="notes-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course.id


async def _auth(client: AsyncClient, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    return {"Authorization": f"Bearer {token}"}


async def test_store_creates_and_show_returns(client: AsyncClient):
    course_id = await _make_course()
    headers = await _auth(client, "n1@aiacademy.tj")

    r = await client.post(
        "/api/v1/personal-notes",
        headers=headers,
        data={
            "item_type": "text_lesson",
            "item_id": "7",
            "course_id": str(course_id),
            "note": "remember this",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["note"] == "remember this"
    assert body["target_type"] == "text_lesson"
    assert body["target_id"] == 7

    r = await client.get(
        "/api/v1/personal-notes", headers=headers, params={"type": "text_lesson", "item": 7}
    )
    assert r.status_code == 200
    assert r.json()["note"] == "remember this"


async def test_store_upserts(client: AsyncClient):
    course_id = await _make_course()
    headers = await _auth(client, "n2@aiacademy.tj")
    base = {"item_type": "file", "item_id": "3", "course_id": str(course_id)}

    r1 = await client.post("/api/v1/personal-notes", headers=headers, data={**base, "note": "v1"})
    r2 = await client.post("/api/v1/personal-notes", headers=headers, data={**base, "note": "v2"})
    assert r1.json()["id"] == r2.json()["id"]  # same row updated
    assert r2.json()["note"] == "v2"


async def test_show_404_when_absent(client: AsyncClient):
    headers = await _auth(client, "n3@aiacademy.tj")
    r = await client.get(
        "/api/v1/personal-notes", headers=headers, params={"type": "quiz", "item": 99}
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "not_found"


async def test_show_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/personal-notes", params={"type": "quiz", "item": 1})
    assert r.status_code == 401


async def test_show_rejects_bad_type(client: AsyncClient):
    headers = await _auth(client, "n4@aiacademy.tj")
    r = await client.get(
        "/api/v1/personal-notes", headers=headers, params={"type": "bogus", "item": 1}
    )
    assert r.status_code == 422


async def test_destroy_scoped_to_owner(client: AsyncClient):
    course_id = await _make_course()
    owner = await _auth(client, "owner@aiacademy.tj")
    other = await _auth(client, "other@aiacademy.tj")

    r = await client.post(
        "/api/v1/personal-notes",
        headers=owner,
        data={
            "item_type": "session",
            "item_id": "1",
            "course_id": str(course_id),
            "note": "mine",
        },
    )
    note_id = r.json()["id"]

    # another user cannot delete it
    r = await client.delete(f"/api/v1/personal-notes/delete/{note_id}", headers=other)
    assert r.status_code == 404

    # owner can
    r = await client.delete(f"/api/v1/personal-notes/delete/{note_id}", headers=owner)
    assert r.status_code == 200

    # gone now
    r = await client.get(
        "/api/v1/personal-notes", headers=owner, params={"type": "session", "item": 1}
    )
    assert r.status_code == 404
