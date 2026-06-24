from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _make_teacher(email: str) -> int:
    async with AsyncSessionLocal() as db:
        u = User(full_name="Teacher", email=email, password="x", role_id=4, role_name=Role.TEACHER)
        db.add(u)
        await db.commit()
        await db.refresh(u)
        return u.id


async def _auth(client: AsyncClient, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    return {"Authorization": f"Bearer {token}"}


async def test_follow_and_unfollow(client: AsyncClient):
    headers = await _auth(client, "fol1@aiacademy.tj")
    target = await _make_teacher("fol-target1@aiacademy.tj")

    r = await client.post(f"/api/v1/users/{target}/follow", headers=headers, json={"status": True})
    assert r.status_code == 200
    assert r.json()["status"] == "followed"

    # reflected on the public profile + in following list
    r = await client.get(f"/api/v1/users/{target}/profile", headers=headers)
    assert r.json()["is_following"] is True
    assert r.json()["followers_count"] == 1

    r = await client.get("/api/v1/panel/following", headers=headers)
    assert [u["id"] for u in r.json()] == [target]

    # unfollow
    r = await client.post(f"/api/v1/users/{target}/follow", headers=headers, json={"status": False})
    assert r.json()["status"] == "unfollowed"
    r = await client.get(f"/api/v1/users/{target}/profile", headers=headers)
    assert r.json()["is_following"] is False
    assert r.json()["followers_count"] == 0


async def test_follow_idempotent(client: AsyncClient):
    headers = await _auth(client, "fol2@aiacademy.tj")
    target = await _make_teacher("fol-target2@aiacademy.tj")
    await client.post(f"/api/v1/users/{target}/follow", headers=headers, json={"status": True})
    await client.post(f"/api/v1/users/{target}/follow", headers=headers, json={"status": True})
    r = await client.get(f"/api/v1/users/{target}/profile", headers=headers)
    assert r.json()["followers_count"] == 1


async def test_cannot_follow_self(client: AsyncClient):
    token, uid = await register_verified_user(client, "fol3@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(f"/api/v1/users/{uid}/follow", headers=headers, json={"status": True})
    assert r.status_code == 400
    assert r.json()["detail"] == "cannot_follow_self"


async def test_follow_missing_user_404(client: AsyncClient):
    headers = await _auth(client, "fol4@aiacademy.tj")
    r = await client.post("/api/v1/users/9999/follow", headers=headers, json={"status": True})
    assert r.status_code == 404


async def test_follow_requires_auth(client: AsyncClient):
    r = await client.post("/api/v1/users/1/follow", json={"status": True})
    assert r.status_code == 401


async def test_profile_following_false_when_anonymous(client: AsyncClient):
    target = await _make_teacher("fol-target5@aiacademy.tj")
    r = await client.get(f"/api/v1/users/{target}/profile")
    assert r.json()["is_following"] is False
