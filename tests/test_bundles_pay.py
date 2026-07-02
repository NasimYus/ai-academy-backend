from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.bundle import Bundle, BundleStatus, BundleWebinar
from app.models.course import Course, CourseStatus, CourseType
from app.models.payment import PaymentChannel, PaymentChannelStatus
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _seller(client: AsyncClient, email: str = "bseller@aiacademy.tj") -> int:
    _, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return uid


async def _bundle(seller_id: int, price: float, n_courses: int = 2) -> tuple[int, list[int]]:
    async with AsyncSessionLocal() as db:
        bundle = Bundle(
            title="Pro pack",
            slug=f"pack-{seller_id}-{price}",
            status=BundleStatus.active,
            price=price,
            creator_id=seller_id,
            teacher_id=seller_id,
        )
        db.add(bundle)
        await db.flush()
        course_ids = []
        for i in range(n_courses):
            c = Course(
                title=f"bc{i}-{seller_id}",
                slug=f"bc{i}-{seller_id}-{price}",
                type=CourseType.course,
                status=CourseStatus.active,
                price=50,
                teacher_id=seller_id,
                creator_id=seller_id,
            )
            db.add(c)
            await db.flush()
            db.add(BundleWebinar(bundle_id=bundle.id, course_id=c.id, creator_id=seller_id))
            course_ids.append(c.id)
        await db.commit()
        return bundle.id, course_ids


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


async def test_pay_bundle_creates_order_then_grants_on_paid(client: AsyncClient):
    seller_id = await _seller(client)
    gid = await _channel()
    bundle_id, course_ids = await _bundle(seller_id, price=120)

    buyer_token, buyer_id = await register_verified_user(client, email="bbuyer@aiacademy.tj")

    # create the pending order for the bundle
    r = await client.post(f"/api/v1/bundles/{bundle_id}/pay", headers=_auth(buyer_token))
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["status"] == "pending"
    assert order["total_amount"] == 120.0
    assert order["items"][0]["bundle_id"] == bundle_id
    assert order["items"][0]["title"] == "Pro pack"
    order_id = order["id"]

    # pay it through the normal gateway flow
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

    # buyer is enrolled in every bundle course
    mine = (await client.get("/api/v1/panel/my-courses", headers=_auth(buyer_token))).json()
    enrolled_ids = {c["id"] for c in mine}
    assert set(course_ids) <= enrolled_ids


async def test_pay_bundle_records_bundle_sale(client: AsyncClient):
    seller_id = await _seller(client, email="bseller2@aiacademy.tj")
    gid = await _channel()
    bundle_id, _ = await _bundle(seller_id, price=90)
    buyer_token, _ = await register_verified_user(client, email="bbuyer2@aiacademy.tj")

    order_id = (
        await client.post(f"/api/v1/bundles/{bundle_id}/pay", headers=_auth(buyer_token))
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

    # seller logs in to view sales
    seller_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "bseller2@aiacademy.tj", "password": "Secret123!"},
    )
    seller_token = seller_login.json()["access_token"]
    sales = (await client.get("/api/v1/panel/sales", headers=_auth(seller_token))).json()
    assert sales["count"] == 1
    assert sales["sales"][0]["type"] == "bundle"
    assert sales["sales"][0]["bundle_id"] == bundle_id
    assert sales["total_income"] == 90.0


async def test_pay_free_bundle_rejected(client: AsyncClient):
    seller_id = await _seller(client, email="bseller3@aiacademy.tj")
    bundle_id, _ = await _bundle(seller_id, price=0)
    buyer_token, _ = await register_verified_user(client, email="bbuyer3@aiacademy.tj")
    r = await client.post(f"/api/v1/bundles/{bundle_id}/pay", headers=_auth(buyer_token))
    assert r.status_code == 422
    assert r.json()["detail"] == "not_free"


async def test_pay_bundle_already_purchased(client: AsyncClient):
    seller_id = await _seller(client, email="bseller4@aiacademy.tj")
    gid = await _channel()
    bundle_id, _ = await _bundle(seller_id, price=70)
    buyer_token, _ = await register_verified_user(client, email="bbuyer4@aiacademy.tj")

    # first purchase
    order_id = (
        await client.post(f"/api/v1/bundles/{bundle_id}/pay", headers=_auth(buyer_token))
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

    # second attempt rejected
    again = await client.post(f"/api/v1/bundles/{bundle_id}/pay", headers=_auth(buyer_token))
    assert again.status_code == 422
    assert again.json()["detail"] == "already_purchased"
