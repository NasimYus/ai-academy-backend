from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _admin(client: AsyncClient, email: str = "useradmin@aiacademy.tj") -> tuple[str, int]:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.ADMIN
        user.role_id = 2
        await db.commit()
    return token, uid


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_non_admin_forbidden(client: AsyncClient):
    token, _ = await register_verified_user(client)
    r = await client.get("/api/v1/admin/users", headers=_auth(token))
    assert r.status_code == 403


async def test_list_and_filter(client: AsyncClient):
    admin_token, _ = await _admin(client)
    await register_verified_user(client, email="stud1@aiacademy.tj")
    await register_verified_user(client, email="stud2@aiacademy.tj")

    full = (await client.get("/api/v1/admin/users", headers=_auth(admin_token))).json()
    assert full["count"] >= 3  # 2 students + admin

    students = (
        await client.get("/api/v1/admin/users?role=user", headers=_auth(admin_token))
    ).json()
    assert all(u["role_name"] == "user" for u in students["users"])
    assert students["count"] >= 2


async def test_ban_and_unban_blocks_login(client: AsyncClient):
    admin_token, _ = await _admin(client)
    _, victim_id = await register_verified_user(client, email="victim@aiacademy.tj")

    banned = await client.post(
        f"/api/v1/admin/users/{victim_id}/ban", headers=_auth(admin_token), json={"days": 7}
    )
    assert banned.status_code == 200
    assert banned.json()["ban"] is True
    assert banned.json()["ban_end_at"] is not None

    # login now blocked
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "victim@aiacademy.tj", "password": "secret12345"},
    )
    assert login.status_code == 403
    assert login.json()["detail"] == "banned_account"

    # unban restores access
    unbanned = await client.post(
        f"/api/v1/admin/users/{victim_id}/unban", headers=_auth(admin_token)
    )
    assert unbanned.json()["ban"] is False
    login2 = await client.post(
        "/api/v1/auth/login",
        json={"username": "victim@aiacademy.tj", "password": "secret12345"},
    )
    assert login2.status_code == 200


async def test_permanent_ban_sets_far_future(client: AsyncClient):
    admin_token, _ = await _admin(client)
    _, uid = await register_verified_user(client, email="perma@aiacademy.tj")
    r = await client.post(f"/api/v1/admin/users/{uid}/ban", headers=_auth(admin_token), json={})
    assert r.json()["ban"] is True
    assert r.json()["ban_end_at"] is not None  # far-future, not null


async def test_set_role(client: AsyncClient):
    admin_token, _ = await _admin(client)
    _, uid = await register_verified_user(client, email="promote@aiacademy.tj")

    r = await client.post(
        f"/api/v1/admin/users/{uid}/role", headers=_auth(admin_token), json={"role_id": 4}
    )
    assert r.status_code == 200
    assert r.json()["role_id"] == 4
    assert r.json()["role_name"] == "teacher"


async def test_bad_role_rejected(client: AsyncClient):
    admin_token, _ = await _admin(client)
    _, uid = await register_verified_user(client, email="badrole@aiacademy.tj")
    r = await client.post(
        f"/api/v1/admin/users/{uid}/role", headers=_auth(admin_token), json={"role_id": 999}
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "bad_role"


async def test_cannot_modify_self(client: AsyncClient):
    admin_token, admin_id = await _admin(client)
    r = await client.post(
        f"/api/v1/admin/users/{admin_id}/ban", headers=_auth(admin_token), json={"days": 1}
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "cannot_modify_self"


async def test_ban_missing_user_404(client: AsyncClient):
    admin_token, _ = await _admin(client)
    r = await client.post(
        "/api/v1/admin/users/99999/ban", headers=_auth(admin_token), json={"days": 1}
    )
    assert r.status_code == 404
