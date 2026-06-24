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


async def _make_channel(active: bool = True) -> int:
    async with AsyncSessionLocal() as db:
        ch = PaymentChannel(
            title="Sandbox",
            class_name="Sandbox",
            status=PaymentChannelStatus.active if active else PaymentChannelStatus.inactive,
        )
        db.add(ch)
        await db.commit()
        await db.refresh(ch)
        return ch.id


async def _auth(client: AsyncClient, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    return {"Authorization": f"Bearer {token}"}


async def _order(client: AsyncClient, headers: dict, price: float = 100) -> int:
    c = await _make_course(f"pay-{price}-{headers['Authorization'][-6:]}", price)
    await client.post("/api/v1/cart", headers=headers, json={"item_id": c, "item_name": "webinar"})
    r = await client.post("/api/v1/cart/checkout", headers=headers, json={})
    return r.json()["id"]


async def test_list_channels(client: AsyncClient):
    headers = await _auth(client, "pay1@aiacademy.tj")
    await _make_channel()
    r = await client.get("/api/v1/payments/channels", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["class_name"] == "Sandbox"


async def test_full_payment_flow(client: AsyncClient):
    headers = await _auth(client, "pay2@aiacademy.tj")
    gid = await _make_channel()
    order_id = await _order(client, headers, 150)

    # request -> paying
    r = await client.post(
        "/api/v1/payments/request",
        headers=headers,
        json={"order_id": order_id, "gateway_id": gid},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paying"
    assert "order_id=" in r.json()["redirect_url"]

    # verify success -> paid
    r = await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=headers,
        json={"order_id": order_id, "status": "success"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"


async def test_verify_failed_marks_fail(client: AsyncClient):
    headers = await _auth(client, "pay3@aiacademy.tj")
    gid = await _make_channel()
    order_id = await _order(client, headers, 80)
    await client.post(
        "/api/v1/payments/request", headers=headers, json={"order_id": order_id, "gateway_id": gid}
    )
    r = await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=headers,
        json={"order_id": order_id, "status": "failed"},
    )
    assert r.json()["status"] == "fail"


async def test_request_rejects_inactive_gateway(client: AsyncClient):
    headers = await _auth(client, "pay4@aiacademy.tj")
    gid = await _make_channel(active=False)
    order_id = await _order(client, headers, 50)
    r = await client.post(
        "/api/v1/payments/request", headers=headers, json={"order_id": order_id, "gateway_id": gid}
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "disabled_gateway"


async def test_request_rejects_non_pending(client: AsyncClient):
    headers = await _auth(client, "pay5@aiacademy.tj")
    gid = await _make_channel()
    order_id = await _order(client, headers, 60)
    # move to paying
    await client.post(
        "/api/v1/payments/request", headers=headers, json={"order_id": order_id, "gateway_id": gid}
    )
    # second request -> not pending
    r = await client.post(
        "/api/v1/payments/request", headers=headers, json={"order_id": order_id, "gateway_id": gid}
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "not_pending"


async def test_verify_requires_paying(client: AsyncClient):
    headers = await _auth(client, "pay6@aiacademy.tj")
    await _make_channel()
    order_id = await _order(client, headers, 70)
    # verify before request (order still pending)
    r = await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=headers,
        json={"order_id": order_id, "status": "success"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "not_paying"


async def test_request_requires_auth(client: AsyncClient):
    r = await client.post("/api/v1/payments/request", json={"order_id": 1, "gateway_id": 1})
    assert r.status_code == 401


async def test_order_owner_scoped(client: AsyncClient):
    owner = await _auth(client, "pay-owner@aiacademy.tj")
    other = await _auth(client, "pay-other@aiacademy.tj")
    gid = await _make_channel()
    order_id = await _order(client, owner, 90)
    r = await client.post(
        "/api/v1/payments/request", headers=other, json={"order_id": order_id, "gateway_id": gid}
    )
    assert r.status_code == 404
