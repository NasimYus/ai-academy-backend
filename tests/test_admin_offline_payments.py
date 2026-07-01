from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _admin(client: AsyncClient, email: str = "payadmin@aiacademy.tj") -> str:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.ADMIN
        user.role_id = 2
        await db.commit()
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _submit_topup(client: AsyncClient, token: str, amount: float) -> int:
    r = await client.post(
        "/api/v1/panel/financial/offline-payments",
        json={"amount": amount, "bank": "Amonatbonk", "reference_number": "R-1"},
        headers=_auth(token),
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _balance(client: AsyncClient, token: str) -> float:
    r = await client.get("/api/v1/panel/financial/account", headers=_auth(token))
    return r.json()["charge"]


async def test_approve_credits_wallet(client: AsyncClient):
    admin = await _admin(client)
    student, _ = await register_verified_user(client, email="topupuser@aiacademy.tj")

    assert await _balance(client, student) == 0
    pid = await _submit_topup(client, student, 150)
    assert await _balance(client, student) == 0  # still waiting

    # admin sees it in the waiting list
    waiting = await client.get(
        "/api/v1/admin/offline-payments", params={"status": "waiting"}, headers=_auth(admin)
    )
    assert any(p["id"] == pid for p in waiting.json())

    # approve -> wallet credited
    ok = await client.post(
        f"/api/v1/admin/offline-payments/{pid}/approve", headers=_auth(admin)
    )
    assert ok.status_code == 200 and ok.json()["status"] == "approved"
    assert await _balance(client, student) == 150

    # re-approving a non-waiting payment is rejected
    again = await client.post(
        f"/api/v1/admin/offline-payments/{pid}/approve", headers=_auth(admin)
    )
    assert again.status_code == 422
    assert again.json()["detail"] == "not_waiting"


async def test_reject_does_not_credit(client: AsyncClient):
    admin = await _admin(client, email="payadmin2@aiacademy.tj")
    student, _ = await register_verified_user(client, email="topupuser2@aiacademy.tj")
    pid = await _submit_topup(client, student, 90)

    r = await client.post(f"/api/v1/admin/offline-payments/{pid}/reject", headers=_auth(admin))
    assert r.status_code == 200 and r.json()["status"] == "reject"
    assert await _balance(client, student) == 0


async def test_non_admin_forbidden(client: AsyncClient):
    student, _ = await register_verified_user(client, email="notadmin@aiacademy.tj")
    r = await client.get("/api/v1/admin/offline-payments", headers=_auth(student))
    assert r.status_code == 403
