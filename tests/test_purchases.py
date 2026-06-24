from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.payment import PaymentChannel, PaymentChannelStatus
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


async def _channel() -> int:
    async with AsyncSessionLocal() as db:
        ch = PaymentChannel(
            title="Sandbox", class_name="Sandbox", status=PaymentChannelStatus.active
        )
        db.add(ch)
        await db.commit()
        await db.refresh(ch)
        return ch.id


async def _auth(client: AsyncClient, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    return {"Authorization": f"Bearer {token}"}


async def _checkout(client: AsyncClient, headers: dict, course_id: int) -> int:
    await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": course_id, "item_name": "webinar"}
    )
    return (await client.post("/api/v1/cart/checkout", headers=headers, json={})).json()["id"]


async def _pay(client: AsyncClient, headers: dict, order_id: int, gid: int) -> None:
    await client.post(
        "/api/v1/payments/request", headers=headers, json={"order_id": order_id, "gateway_id": gid}
    )
    await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=headers,
        json={"order_id": order_id, "status": "success"},
    )


async def test_purchases_lists_only_paid(client: AsyncClient):
    headers = await _auth(client, "pur1@aiacademy.tj")
    gid = await _channel()
    paid_course = await _make_course("pur-paid", 200)
    pending_course = await _make_course("pur-pending", 300)

    # one paid order
    order_id = await _checkout(client, headers, paid_course)
    await _pay(client, headers, order_id, gid)
    # one pending order (not paid)
    await _checkout(client, headers, pending_course)

    r = await client.get("/api/v1/panel/purchases", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["slug"] == "pur-paid"
    assert body[0]["amount"] == 200
    assert body[0]["order_id"] == order_id


async def test_purchases_empty(client: AsyncClient):
    headers = await _auth(client, "pur2@aiacademy.tj")
    r = await client.get("/api/v1/panel/purchases", headers=headers)
    assert r.json() == []


async def test_purchases_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/panel/purchases")
    assert r.status_code == 401
