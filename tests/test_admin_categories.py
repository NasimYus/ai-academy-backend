from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _admin(client: AsyncClient, email: str = "catadmin@aiacademy.tj") -> str:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.ADMIN
        user.role_id = 2
        await db.commit()
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_non_admin_forbidden(client: AsyncClient):
    token, _ = await register_verified_user(client)
    r = await client.get("/api/v1/admin/categories", headers=_auth(token))
    assert r.status_code == 403


async def test_category_crud(client: AsyncClient):
    token = await _admin(client)

    created = await client.post(
        "/api/v1/admin/categories", json={"title": "Программирование"}, headers=_auth(token)
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Программирование" and body["slug"]
    cid = body["id"]

    # public list surfaces it (enabled, top-level)
    pub = await client.get("/api/v1/categories")
    assert any(c["title"] == "Программирование" for c in pub.json()["categories"])

    # rename
    up = await client.put(
        f"/api/v1/admin/categories/{cid}", json={"title": "Веб-разработка"}, headers=_auth(token)
    )
    assert up.json()["title"] == "Веб-разработка"

    # sub-category
    sub = await client.post(
        "/api/v1/admin/categories",
        json={"title": "React", "parent_id": cid},
        headers=_auth(token),
    )
    assert sub.json()["parent_id"] == cid

    listed = await client.get("/api/v1/admin/categories", headers=_auth(token))
    assert len(listed.json()) == 2

    # delete
    dl = await client.delete(f"/api/v1/admin/categories/{cid}", headers=_auth(token))
    assert dl.status_code == 204
