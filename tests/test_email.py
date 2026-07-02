from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.payment import PaymentChannel, PaymentChannelStatus
from app.services.email import outbox
from tests.conftest import register_verified_user


async def test_registration_sends_verification_email(client: AsyncClient):
    email = "mailer1@aiacademy.tj"
    r = await client.post(
        "/api/v1/auth/register/step/1",
        json={"email": email, "password": "Secret123!", "password_confirmation": "Secret123!"},
    )
    assert r.status_code == 200
    sent = [m for m in outbox.messages if m.to == email]
    assert len(sent) == 1
    assert "код" in sent[0].subject.lower()
    # the code surfaced in debug should appear in the email body
    assert str(r.json()["code"]) in sent[0].body


async def test_forgot_password_sends_reset_email(client: AsyncClient):
    email = "mailer2@aiacademy.tj"
    # register + verify so the account exists
    r = await client.post(
        "/api/v1/auth/register/step/1",
        json={"email": email, "password": "Secret123!", "password_confirmation": "Secret123!"},
    )
    body = r.json()
    await client.post(
        "/api/v1/auth/register/step/2", json={"user_id": body["user_id"], "code": body["code"]}
    )
    await client.post(
        "/api/v1/auth/register/step/3", json={"user_id": body["user_id"], "full_name": "Mailer"}
    )
    outbox.clear()

    r = await client.post("/api/v1/auth/forget-password", json={"type": "email", "email": email})
    assert r.status_code == 200
    sent = [m for m in outbox.messages if m.to == email]
    assert len(sent) == 1
    assert "reset-password?token=" in sent[0].body


async def test_no_email_for_unknown_recipient(client: AsyncClient):
    # Anti-enumeration: unknown email -> same 200 "done", but no email sent.
    r = await client.post(
        "/api/v1/auth/forget-password", json={"type": "email", "email": "nobody@aiacademy.tj"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert outbox.messages == []


async def test_paid_order_sends_receipt(client: AsyncClient):
    email_addr = "mailer3@aiacademy.tj"
    token, _ = await register_verified_user(client, email_addr)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        course = Course(
            title="Receipt Course",
            slug="receipt-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=120,
        )
        ch = PaymentChannel(
            title="Sandbox", class_name="Sandbox", status=PaymentChannelStatus.active
        )
        db.add_all([course, ch])
        await db.commit()
        await db.refresh(course)
        await db.refresh(ch)
        course_id, gid = course.id, ch.id

    await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": course_id, "item_name": "webinar"}
    )
    order_id = (await client.post("/api/v1/cart/checkout", headers=headers, json={})).json()["id"]
    await client.post(
        "/api/v1/payments/request", headers=headers, json={"order_id": order_id, "gateway_id": gid}
    )
    outbox.clear()
    await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=headers,
        json={"order_id": order_id, "status": "success"},
    )

    sent = [m for m in outbox.messages if m.to == email_addr]
    assert len(sent) == 1
    assert f"#{order_id}" in sent[0].subject
    assert "120" in sent[0].body
