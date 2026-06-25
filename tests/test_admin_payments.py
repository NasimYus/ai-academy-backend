from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _admin(client: AsyncClient, email: str = "admin@aiacademy.tj") -> str:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.ADMIN
        user.role_id = 2
        await db.commit()
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create(client: AsyncClient, token: str, **body) -> dict:
    payload = {"title": "Zarinpal", "class_name": "Zarinpal", **body}
    r = await client.post("/api/v1/admin/payment-channels", json=payload, headers=_auth(token))
    assert r.status_code == 201, r.text
    return r.json()


async def test_non_admin_forbidden(client: AsyncClient):
    token, _ = await register_verified_user(client)
    r = await client.get("/api/v1/admin/payment-channels", headers=_auth(token))
    assert r.status_code == 403


async def test_anonymous_unauthorized(client: AsyncClient):
    r = await client.get("/api/v1/admin/payment-channels")
    assert r.status_code == 401


async def test_create_exposes_credential_contract(client: AsyncClient):
    token = await _admin(client)
    body = await _create(client, token)
    assert body["credential_items"] == ["merchant_id"]
    assert body["supported"] is True
    assert body["show_test_mode_toggle"] is True
    assert body["status"] == "inactive"  # default


async def test_unsupported_driver_flagged(client: AsyncClient):
    token = await _admin(client)
    body = await _create(client, token, title="Stripe", class_name="Stripe")
    assert body["supported"] is False
    assert body["credential_items"] == []


async def test_list_and_get(client: AsyncClient):
    token = await _admin(client)
    created = await _create(client, token)

    lst = (await client.get("/api/v1/admin/payment-channels", headers=_auth(token))).json()
    assert len(lst) == 1
    assert lst[0]["id"] == created["id"]

    got = await client.get(f"/api/v1/admin/payment-channels/{created['id']}", headers=_auth(token))
    assert got.status_code == 200
    assert got.json()["class_name"] == "Zarinpal"


async def test_get_404(client: AsyncClient):
    token = await _admin(client)
    r = await client.get("/api/v1/admin/payment-channels/999", headers=_auth(token))
    assert r.status_code == 404


async def test_update_credentials_and_status(client: AsyncClient):
    token = await _admin(client)
    created = await _create(client, token)

    r = await client.put(
        f"/api/v1/admin/payment-channels/{created['id']}",
        json={
            "title": "Zarinpal TJ",
            "status": "active",
            "test_mode": True,
            "credentials": {"merchant_id": "abc-123"},
            "currencies": ["TJS"],
        },
        headers=_auth(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Zarinpal TJ"
    assert body["status"] == "active"
    assert body["test_mode"] is True
    assert body["credentials"] == {"merchant_id": "abc-123"}
    assert body["currencies"] == ["TJS"]


async def test_toggle_status(client: AsyncClient):
    token = await _admin(client)
    created = await _create(client, token, status="active")
    cid = created["id"]

    off = await client.post(
        f"/api/v1/admin/payment-channels/{cid}/toggle-status", headers=_auth(token)
    )
    assert off.json()["status"] == "inactive"

    on = await client.post(
        f"/api/v1/admin/payment-channels/{cid}/toggle-status", headers=_auth(token)
    )
    assert on.json()["status"] == "active"
