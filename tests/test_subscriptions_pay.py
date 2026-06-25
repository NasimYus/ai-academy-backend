from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.payment import PaymentChannel, PaymentChannelStatus
from app.models.subscription import Subscribe
from tests.conftest import register_verified_user


async def _plan(price: float, days: int = 30, usable: int = 5) -> int:
    async with AsyncSessionLocal() as db:
        plan = Subscribe(title="Pro", usable_count=usable, days=days, price=price)
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan.id


async def _channel() -> int:
    async with AsyncSessionLocal() as db:
        ch = PaymentChannel(
            title="Sandbox", class_name="Sandbox", status=PaymentChannelStatus.active
        )
        db.add(ch)
        await db.commit()
        await db.refresh(ch)
        return ch.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _pay_order(client: AsyncClient, token: str, order_id: int, gid: int) -> dict:
    await client.post(
        "/api/v1/payments/request",
        headers=_auth(token),
        json={"order_id": order_id, "gateway_id": gid},
    )
    r = await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=_auth(token),
        json={"order_id": order_id, "status": "success"},
    )
    return r.json()


async def test_pay_subscription_activates_on_paid(client: AsyncClient):
    gid = await _channel()
    plan_id = await _plan(price=200)
    token, _ = await register_verified_user(client, email="sub-buyer@aiacademy.tj")

    # no active subscription yet
    before = (await client.get("/api/v1/subscribe", headers=_auth(token))).json()
    assert before["subscribed"] is None

    # create order for the paid plan
    r = await client.post(f"/api/v1/subscribe/{plan_id}/pay", headers=_auth(token))
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["status"] == "pending"
    assert order["total_amount"] == 200.0
    assert order["items"][0]["subscribe_id"] == plan_id
    assert order["items"][0]["title"] == "Pro"

    paid = await _pay_order(client, token, order["id"], gid)
    assert paid["status"] == "paid"

    # subscription is now active
    after = (await client.get("/api/v1/subscribe", headers=_auth(token))).json()
    assert after["subscribed"] is not None
    assert after["subscribed"]["remaining"] == 5


async def test_pay_subscription_records_subscribe_sale(client: AsyncClient):
    gid = await _channel()
    plan_id = await _plan(price=150)
    token, _ = await register_verified_user(client, email="sub-buyer2@aiacademy.tj")

    order_id = (await client.post(f"/api/v1/subscribe/{plan_id}/pay", headers=_auth(token))).json()[
        "id"
    ]
    await _pay_order(client, token, order_id, gid)

    # the buyer's purchase history reflects nothing course-specific, but the Sale
    # exists with type=subscribe — verify via the order item ref round-trip.
    orders = (await client.get("/api/v1/panel/orders", headers=_auth(token))).json()
    assert orders[0]["items"][0]["subscribe_id"] == plan_id


async def test_pay_free_plan_rejected(client: AsyncClient):
    plan_id = await _plan(price=0)
    token, _ = await register_verified_user(client, email="sub-free@aiacademy.tj")
    r = await client.post(f"/api/v1/subscribe/{plan_id}/pay", headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "not_free"


async def test_pay_missing_plan_404(client: AsyncClient):
    token, _ = await register_verified_user(client, email="sub-404@aiacademy.tj")
    r = await client.post("/api/v1/subscribe/999/pay", headers=_auth(token))
    assert r.status_code == 404
