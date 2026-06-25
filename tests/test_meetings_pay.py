from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.payment import PaymentChannel, PaymentChannelStatus
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _teacher(client: AsyncClient, email: str = "mseller@aiacademy.tj") -> tuple[str, int]:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return token, uid


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


async def _setup_paid_meeting(client: AsyncClient, seller_token: str, amount: int) -> int:
    """Configure a paid meeting + one slot; return the time id."""
    await client.put(
        "/api/v1/panel/meeting",
        json={"amount": amount, "disabled": False},
        headers=_auth(seller_token),
    )
    r = await client.post(
        "/api/v1/panel/meeting/times",
        json={"day_label": "monday", "time": "10:00-11:00"},
        headers=_auth(seller_token),
    )
    return r.json()["id"]


async def _reserve(client: AsyncClient, token: str, time_id: int) -> int:
    r = await client.post(
        "/api/v1/meetings/reserve",
        json={"meeting_time_id": time_id},
        headers=_auth(token),
    )
    return r.json()["id"]


async def test_pay_reservation_confirms_and_records_meeting_sale(client: AsyncClient):
    seller_token, seller_id = await _teacher(client)
    gid = await _channel()
    time_id = await _setup_paid_meeting(client, seller_token, amount=300)

    buyer_token, _ = await register_verified_user(client, email="mbuyer@aiacademy.tj")
    reserve_id = await _reserve(client, buyer_token, time_id)

    # create the order for the reservation
    r = await client.post(f"/api/v1/meetings/reserve/{reserve_id}/pay", headers=_auth(buyer_token))
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["total_amount"] == 300.0
    assert order["items"][0]["reserve_meeting_id"] == reserve_id
    assert order["items"][0]["title"] == "Консультация"
    order_id = order["id"]

    # pay it
    await client.post(
        "/api/v1/payments/request",
        headers=_auth(buyer_token),
        json={"order_id": order_id, "gateway_id": gid},
    )
    paid = await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=_auth(buyer_token),
        json={"order_id": order_id, "status": "success"},
    )
    assert paid.json()["status"] == "paid"

    # reservation is now open (confirmed)
    shown = (
        await client.get(f"/api/v1/panel/meetings/{reserve_id}", headers=_auth(buyer_token))
    ).json()
    assert shown["status"] == "open"

    # a meeting Sale is recorded for the instructor
    sales = (await client.get("/api/v1/panel/sales", headers=_auth(seller_token))).json()
    assert sales["count"] == 1
    assert sales["sales"][0]["type"] == "meeting"
    assert sales["total_income"] == 300.0


async def test_pay_reservation_twice_rejected(client: AsyncClient):
    seller_token, _ = await _teacher(client, email="mseller2@aiacademy.tj")
    gid = await _channel()
    time_id = await _setup_paid_meeting(client, seller_token, amount=120)
    buyer_token, _ = await register_verified_user(client, email="mbuyer2@aiacademy.tj")
    reserve_id = await _reserve(client, buyer_token, time_id)

    order_id = (
        await client.post(f"/api/v1/meetings/reserve/{reserve_id}/pay", headers=_auth(buyer_token))
    ).json()["id"]
    await client.post(
        "/api/v1/payments/request",
        headers=_auth(buyer_token),
        json={"order_id": order_id, "gateway_id": gid},
    )
    await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=_auth(buyer_token),
        json={"order_id": order_id, "status": "success"},
    )

    again = await client.post(
        f"/api/v1/meetings/reserve/{reserve_id}/pay", headers=_auth(buyer_token)
    )
    assert again.status_code == 422
    assert again.json()["detail"] == "already_paid"


async def test_pay_free_reservation_rejected(client: AsyncClient):
    seller_token, _ = await _teacher(client, email="mseller3@aiacademy.tj")
    time_id = await _setup_paid_meeting(client, seller_token, amount=0)
    buyer_token, _ = await register_verified_user(client, email="mbuyer3@aiacademy.tj")
    reserve_id = await _reserve(client, buyer_token, time_id)
    r = await client.post(f"/api/v1/meetings/reserve/{reserve_id}/pay", headers=_auth(buyer_token))
    assert r.status_code == 422
    assert r.json()["detail"] == "not_free"


async def test_pay_foreign_reservation_404(client: AsyncClient):
    seller_token, _ = await _teacher(client, email="mseller4@aiacademy.tj")
    time_id = await _setup_paid_meeting(client, seller_token, amount=100)
    buyer_token, _ = await register_verified_user(client, email="mbuyer4@aiacademy.tj")
    reserve_id = await _reserve(client, buyer_token, time_id)

    other_token, _ = await register_verified_user(client, email="mother@aiacademy.tj")
    r = await client.post(f"/api/v1/meetings/reserve/{reserve_id}/pay", headers=_auth(other_token))
    assert r.status_code == 404
