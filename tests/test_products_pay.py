from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.payment import PaymentChannel, PaymentChannelStatus
from app.models.product import Product, ProductStatus, ProductType
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _seller(client: AsyncClient, email: str = "pseller@aiacademy.tj") -> int:
    _, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return uid


async def _product(
    seller_id: int, price: float, ptype: ProductType = ProductType.virtual, delivery: float = 0
) -> int:
    async with AsyncSessionLocal() as db:
        p = Product(
            title="Gadget",
            type=ptype,
            status=ProductStatus.active,
            ordering=True,
            price=price,
            delivery_fee=delivery,
            creator_id=seller_id,
        )
        db.add(p)
        await db.commit()
        await db.refresh(p)
        return p.id


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


async def test_buy_virtual_product_success_and_sale(client: AsyncClient):
    seller_id = await _seller(client)
    gid = await _channel()
    product_id = await _product(seller_id, price=50)
    buyer_token, _ = await register_verified_user(client, email="pbuyer@aiacademy.tj")

    r = await client.post(
        f"/api/v1/products/{product_id}/pay", headers=_auth(buyer_token), json={"quantity": 2}
    )
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["total_amount"] == 100.0  # 50 * 2
    assert order["items"][0]["product_id"] == product_id
    assert order["items"][0]["title"] == "Gadget"

    assert (await _pay(client, buyer_token, order["id"], gid))["status"] == "paid"

    # virtual product order → success
    orders = (await client.get("/api/v1/panel/product-orders", headers=_auth(buyer_token))).json()
    assert len(orders) == 1
    assert orders[0]["status"] == "success"
    assert orders[0]["quantity"] == 2

    # product Sale recorded for the seller
    seller_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "pseller@aiacademy.tj", "password": "secret12345"},
    )
    seller_token = seller_login.json()["access_token"]
    sales = (await client.get("/api/v1/panel/sales", headers=_auth(seller_token))).json()
    assert sales["count"] == 1
    assert sales["sales"][0]["type"] == "product"
    assert sales["sales"][0]["product_id"] == product_id


async def test_buy_physical_product_awaits_delivery(client: AsyncClient):
    seller_id = await _seller(client, email="pseller2@aiacademy.tj")
    gid = await _channel()
    product_id = await _product(seller_id, price=30, ptype=ProductType.physical, delivery=10)
    buyer_token, _ = await register_verified_user(client, email="pbuyer2@aiacademy.tj")

    order = (
        await client.post(
            f"/api/v1/products/{product_id}/pay", headers=_auth(buyer_token), json={"quantity": 1}
        )
    ).json()
    assert order["total_amount"] == 40.0  # 30 + 10 delivery
    await _pay(client, buyer_token, order["id"], gid)

    orders = (await client.get("/api/v1/panel/product-orders", headers=_auth(buyer_token))).json()
    assert orders[0]["status"] == "waiting_delivery"


async def test_buy_free_product_rejected(client: AsyncClient):
    seller_id = await _seller(client, email="pseller3@aiacademy.tj")
    product_id = await _product(seller_id, price=0)
    buyer_token, _ = await register_verified_user(client, email="pbuyer3@aiacademy.tj")
    r = await client.post(f"/api/v1/products/{product_id}/pay", headers=_auth(buyer_token), json={})
    assert r.status_code == 422
    assert r.json()["detail"] == "not_free"


async def test_buy_missing_product_404(client: AsyncClient):
    buyer_token, _ = await register_verified_user(client, email="pbuyer4@aiacademy.tj")
    r = await client.post("/api/v1/products/999/pay", headers=_auth(buyer_token), json={})
    assert r.status_code == 404
