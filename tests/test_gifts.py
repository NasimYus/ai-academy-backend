from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.payment import PaymentChannel, PaymentChannelStatus
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _teacher(client: AsyncClient, email: str = "giftseller@aiacademy.tj") -> int:
    _, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return uid


async def _course(slug: str, price: float, creator_id: int) -> int:
    async with AsyncSessionLocal() as db:
        c = Course(
            title=slug,
            slug=slug,
            type=CourseType.course,
            status=CourseStatus.active,
            price=price,
            creator_id=creator_id,
            teacher_id=creator_id,
        )
        db.add(c)
        await db.commit()
        await db.refresh(c)
        return c.id


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


async def _pay(client: AsyncClient, token: str, order_id: int, gid: int) -> dict:
    await client.post(
        "/api/v1/payments/request",
        headers=_auth(token),
        json={"order_id": order_id, "gateway_id": gid},
    )
    return (
        await client.post(
            "/api/v1/payments/verify/Sandbox",
            headers=_auth(token),
            json={"order_id": order_id, "status": "success"},
        )
    ).json()


def _gift_body(course_id: int, email: str) -> dict:
    return {"item_type": "course", "item_id": course_id, "name": "Друг", "email": email}


async def test_gift_paid_enrols_existing_recipient_and_records_sale(client: AsyncClient):
    seller_id = await _teacher(client)
    gid = await _channel()
    course_id = await _course("gift-course", 120, seller_id)

    # recipient already has an account
    recipient_token, _ = await register_verified_user(client, email="recipient@aiacademy.tj")
    sender_token, _ = await register_verified_user(client, email="sender@aiacademy.tj")

    r = await client.post(
        "/api/v1/gifts",
        headers=_auth(sender_token),
        json=_gift_body(course_id, "recipient@aiacademy.tj"),
    )
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["total_amount"] == 120.0
    assert order["items"][0]["gift_id"] is not None
    assert order["items"][0]["title"] == "Подарок"

    assert (await _pay(client, sender_token, order["id"], gid))["status"] == "paid"

    # recipient is auto-enrolled
    mine = (await client.get("/api/v1/panel/my-courses", headers=_auth(recipient_token))).json()
    assert course_id in {c["id"] for c in mine}

    # recipient sees the gift in their inbox
    received = (
        await client.get("/api/v1/panel/gifts/received", headers=_auth(recipient_token))
    ).json()
    assert any(g["item_id"] == course_id and g["status"] == "active" for g in received)

    # gift Sale recorded for the seller
    seller_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "giftseller@aiacademy.tj", "password": "Secret123!"},
    )
    sales = (
        await client.get("/api/v1/panel/sales", headers=_auth(seller_login.json()["access_token"]))
    ).json()
    assert sales["count"] == 1
    assert sales["sales"][0]["type"] == "gift"


async def test_gift_to_unregistered_then_redeem(client: AsyncClient):
    seller_id = await _teacher(client, email="giftseller2@aiacademy.tj")
    gid = await _channel()
    course_id = await _course("gift-course2", 80, seller_id)
    sender_token, _ = await register_verified_user(client, email="sender2@aiacademy.tj")

    order = (
        await client.post(
            "/api/v1/gifts",
            headers=_auth(sender_token),
            json=_gift_body(course_id, "later@aiacademy.tj"),
        )
    ).json()
    await _pay(client, sender_token, order["id"], gid)

    # recipient registers afterwards
    later_token, later_id = await register_verified_user(client, email="later@aiacademy.tj")
    # not auto-enrolled yet
    mine = (await client.get("/api/v1/panel/my-courses", headers=_auth(later_token))).json()
    assert course_id not in {c["id"] for c in mine}

    received = (await client.get("/api/v1/panel/gifts/received", headers=_auth(later_token))).json()
    gift_id = received[0]["id"]
    redeemed = await client.post(f"/api/v1/gifts/{gift_id}/redeem", headers=_auth(later_token))
    assert redeemed.status_code == 200

    mine2 = (await client.get("/api/v1/panel/my-courses", headers=_auth(later_token))).json()
    assert course_id in {c["id"] for c in mine2}


async def test_gift_sent_list(client: AsyncClient):
    seller_id = await _teacher(client, email="giftseller3@aiacademy.tj")
    course_id = await _course("gift-course3", 50, seller_id)
    sender_token, _ = await register_verified_user(client, email="sender3@aiacademy.tj")
    await client.post(
        "/api/v1/gifts",
        headers=_auth(sender_token),
        json=_gift_body(course_id, "x@aiacademy.tj"),
    )
    sent = (await client.get("/api/v1/panel/gifts/sent", headers=_auth(sender_token))).json()
    assert len(sent) == 1
    assert sent[0]["email"] == "x@aiacademy.tj"


async def test_gift_free_course_rejected(client: AsyncClient):
    seller_id = await _teacher(client, email="giftseller4@aiacademy.tj")
    course_id = await _course("gift-free", 0, seller_id)
    sender_token, _ = await register_verified_user(client, email="sender4@aiacademy.tj")
    r = await client.post(
        "/api/v1/gifts",
        headers=_auth(sender_token),
        json=_gift_body(course_id, "y@aiacademy.tj"),
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "not_free"


async def test_gift_missing_item_404(client: AsyncClient):
    sender_token, _ = await register_verified_user(client, email="sender5@aiacademy.tj")
    r = await client.post(
        "/api/v1/gifts", headers=_auth(sender_token), json=_gift_body(99999, "z@aiacademy.tj")
    )
    assert r.status_code == 404


async def test_redeem_not_recipient_forbidden(client: AsyncClient):
    seller_id = await _teacher(client, email="giftseller6@aiacademy.tj")
    gid = await _channel()
    course_id = await _course("gift-course6", 60, seller_id)
    sender_token, _ = await register_verified_user(client, email="sender6@aiacademy.tj")
    order = (
        await client.post(
            "/api/v1/gifts",
            headers=_auth(sender_token),
            json=_gift_body(course_id, "realrecipient@aiacademy.tj"),
        )
    ).json()
    await _pay(client, sender_token, order["id"], gid)

    intruder_token, _ = await register_verified_user(client, email="intruder@aiacademy.tj")
    # intruder has no gift in inbox; try redeeming the sender's gift by id
    sent = (await client.get("/api/v1/panel/gifts/sent", headers=_auth(sender_token))).json()
    r = await client.post(f"/api/v1/gifts/{sent[0]['id']}/redeem", headers=_auth(intruder_token))
    assert r.status_code == 403
