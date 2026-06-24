from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from tests.conftest import register_verified_user


async def _make_course(
    slug: str,
    *,
    price: float = 199,
    private: bool = False,
    status: CourseStatus = CourseStatus.active,
) -> int:
    async with AsyncSessionLocal() as db:
        course = Course(
            title=slug,
            slug=slug,
            type=CourseType.course,
            status=status,
            price=price,
            private=private,
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course.id


async def _auth(client: AsyncClient, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    return {"Authorization": f"Bearer {token}"}


async def test_add_list_remove(client: AsyncClient):
    headers = await _auth(client, "cart1@aiacademy.tj")
    c1 = await _make_course("cart-course-1", price=199)
    c2 = await _make_course("cart-course-2", price=299)

    r = await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": c1, "item_name": "webinar"}
    )
    assert r.status_code == 200
    assert r.json()["course_id"] == c1
    item_id = r.json()["id"]

    await client.post("/api/v1/cart", headers=headers, json={"item_id": c2, "item_name": "webinar"})

    r = await client.get("/api/v1/cart", headers=headers)
    body = r.json()
    assert len(body["items"]) == 2
    assert body["amounts"]["sub_total"] == 498
    assert body["amounts"]["total"] == 498

    r = await client.delete(f"/api/v1/cart/{item_id}", headers=headers)
    assert r.status_code == 200
    r = await client.get("/api/v1/cart", headers=headers)
    assert len(r.json()["items"]) == 1
    assert r.json()["amounts"]["sub_total"] == 299


async def test_add_requires_auth(client: AsyncClient):
    c = await _make_course("cart-noauth", price=10)
    r = await client.post("/api/v1/cart", json={"item_id": c, "item_name": "webinar"})
    assert r.status_code == 401


async def test_duplicate_rejected(client: AsyncClient):
    headers = await _auth(client, "cart2@aiacademy.tj")
    c = await _make_course("cart-dup", price=50)
    await client.post("/api/v1/cart", headers=headers, json={"item_id": c, "item_name": "webinar"})
    r = await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": c, "item_name": "webinar"}
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "already_in_cart"


async def test_already_purchased_rejected(client: AsyncClient):
    headers = await _auth(client, "cart3@aiacademy.tj")
    c = await _make_course("cart-owned", price=0)
    # enrol (free) -> has access
    await client.post(f"/api/v1/panel/courses/{c}/free", headers=headers)
    r = await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": c, "item_name": "webinar"}
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "already_purchased"


async def test_missing_or_private_course_404(client: AsyncClient):
    headers = await _auth(client, "cart4@aiacademy.tj")
    r = await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": 9999, "item_name": "webinar"}
    )
    assert r.status_code == 404

    priv = await _make_course("cart-private", price=10, private=True)
    r = await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": priv, "item_name": "webinar"}
    )
    assert r.status_code == 404


async def test_remove_scoped_to_owner(client: AsyncClient):
    owner = await _auth(client, "cart-owner@aiacademy.tj")
    other = await _auth(client, "cart-other@aiacademy.tj")
    c = await _make_course("cart-scoped", price=10)
    r = await client.post(
        "/api/v1/cart", headers=owner, json={"item_id": c, "item_name": "webinar"}
    )
    item_id = r.json()["id"]

    r = await client.delete(f"/api/v1/cart/{item_id}", headers=other)
    assert r.status_code == 404
    r = await client.delete(f"/api/v1/cart/{item_id}", headers=owner)
    assert r.status_code == 200
