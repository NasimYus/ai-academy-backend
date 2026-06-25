from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.payment import PaymentChannel, PaymentChannelStatus
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _teacher(client: AsyncClient, email: str = "seller@aiacademy.tj") -> tuple[str, int]:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return token, uid


async def _course(slug: str, price: float, teacher_id: int) -> int:
    async with AsyncSessionLocal() as db:
        course = Course(
            title=slug,
            slug=slug,
            type=CourseType.course,
            status=CourseStatus.active,
            price=price,
            teacher_id=teacher_id,
            creator_id=teacher_id,
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


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _buy(client: AsyncClient, headers: dict, course_id: int, gid: int) -> None:
    await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": course_id, "item_name": "webinar"}
    )
    order_id = (await client.post("/api/v1/cart/checkout", headers=headers, json={})).json()["id"]
    await client.post(
        "/api/v1/payments/request", headers=headers, json={"order_id": order_id, "gateway_id": gid}
    )
    r = await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=headers,
        json={"order_id": order_id, "status": "success"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"


async def test_paid_order_records_sale_for_seller(client: AsyncClient):
    seller_token, seller_id = await _teacher(client)
    gid = await _channel()
    course_id = await _course("sale-course", 150, seller_id)

    buyer_headers = _auth((await register_verified_user(client, email="buyer@aiacademy.tj"))[0])
    await _buy(client, buyer_headers, course_id, gid)

    r = await client.get("/api/v1/panel/sales", headers=_auth(seller_token))
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["total_income"] == 150.0
    sale = body["sales"][0]
    assert sale["type"] == "webinar"
    assert sale["webinar_id"] == course_id
    assert sale["seller_id"] == seller_id
    assert sale["total_amount"] == 150.0


async def test_sales_scoped_to_seller(client: AsyncClient):
    seller_token, seller_id = await _teacher(client)
    other_token, _ = await _teacher(client, email="other-seller@aiacademy.tj")
    gid = await _channel()
    course_id = await _course("scoped-course", 80, seller_id)

    buyer_headers = _auth((await register_verified_user(client, email="b2@aiacademy.tj"))[0])
    await _buy(client, buyer_headers, course_id, gid)

    # the other instructor sees none of this seller's sales
    other = (await client.get("/api/v1/panel/sales", headers=_auth(other_token))).json()
    assert other["count"] == 0
    assert other["total_income"] == 0.0


async def test_non_teacher_forbidden(client: AsyncClient):
    token, _ = await register_verified_user(client, email="plain@aiacademy.tj")
    r = await client.get("/api/v1/panel/sales", headers=_auth(token))
    assert r.status_code == 403


async def test_free_enrollment_records_no_sale(client: AsyncClient):
    """A free course enroll goes through enrollment, not checkout — no Sale."""
    seller_token, seller_id = await _teacher(client)
    await _course("free-course", 0, seller_id)

    r = await client.get("/api/v1/panel/sales", headers=_auth(seller_token))
    assert r.json()["count"] == 0
