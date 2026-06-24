from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.discount import Discount, DiscountSource, DiscountType, DiscountUserType
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


async def _percent_coupon(code: str, percent: int) -> int:
    async with AsyncSessionLocal() as db:
        d = Discount(
            title=code,
            code=code,
            discount_type=DiscountType.percentage,
            source=DiscountSource.all,
            user_type=DiscountUserType.all_users,
            percent=percent,
            count=10,
            expired_at=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(d)
        await db.commit()
        await db.refresh(d)
        return d.id


async def _auth(client: AsyncClient, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    return {"Authorization": f"Bearer {token}"}


async def _add(client: AsyncClient, headers: dict, course_id: int) -> None:
    await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": course_id, "item_name": "webinar"}
    )


async def test_checkout_creates_order_and_clears_cart(client: AsyncClient):
    headers = await _auth(client, "ord1@aiacademy.tj")
    c1 = await _make_course("ord-course-1", 200)
    c2 = await _make_course("ord-course-2", 300)
    await _add(client, headers, c1)
    await _add(client, headers, c2)

    r = await client.post("/api/v1/cart/checkout", headers=headers, json={})
    assert r.status_code == 200
    order = r.json()
    assert order["status"] == "pending"
    assert order["amount"] == 500
    assert order["total_amount"] == 500
    assert len(order["items"]) == 2

    # cart is now empty
    r = await client.get("/api/v1/cart", headers=headers)
    assert r.json()["items"] == []

    # order shows up in the list and detail
    r = await client.get("/api/v1/panel/orders", headers=headers)
    assert len(r.json()) == 1
    order_id = r.json()[0]["id"]
    r = await client.get(f"/api/v1/panel/orders/{order_id}", headers=headers)
    assert r.json()["id"] == order_id


async def test_checkout_with_coupon(client: AsyncClient):
    headers = await _auth(client, "ord2@aiacademy.tj")
    c = await _make_course("ord-course-3", 400)
    await _add(client, headers, c)
    did = await _percent_coupon("ORD25", 25)

    r = await client.post("/api/v1/cart/checkout", headers=headers, json={"discount_id": did})
    order = r.json()
    assert order["amount"] == 400
    assert order["total_discount"] == 100  # 25%
    assert order["total_amount"] == 300
    assert order["items"][0]["discount"] == 100
    assert order["items"][0]["total_amount"] == 300


async def test_checkout_empty_cart(client: AsyncClient):
    headers = await _auth(client, "ord3@aiacademy.tj")
    r = await client.post("/api/v1/cart/checkout", headers=headers, json={})
    assert r.status_code == 400
    assert r.json()["detail"] == "empty_cart"


async def test_invalid_coupon_ignored(client: AsyncClient):
    headers = await _auth(client, "ord4@aiacademy.tj")
    c = await _make_course("ord-course-4", 100)
    await _add(client, headers, c)
    # non-existent discount id -> ignored, full price order
    r = await client.post("/api/v1/cart/checkout", headers=headers, json={"discount_id": 9999})
    order = r.json()
    assert order["total_discount"] == 0
    assert order["total_amount"] == 100


async def test_checkout_requires_auth(client: AsyncClient):
    r = await client.post("/api/v1/cart/checkout", json={})
    assert r.status_code == 401


async def test_order_detail_scoped(client: AsyncClient):
    owner = await _auth(client, "ord-owner@aiacademy.tj")
    other = await _auth(client, "ord-other@aiacademy.tj")
    c = await _make_course("ord-course-5", 100)
    await _add(client, owner, c)
    r = await client.post("/api/v1/cart/checkout", headers=owner, json={})
    order_id = r.json()["id"]

    r = await client.get(f"/api/v1/panel/orders/{order_id}", headers=other)
    assert r.status_code == 404
