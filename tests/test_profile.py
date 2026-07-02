from httpx import AsyncClient

from tests.conftest import register_verified_user


async def test_get_and_update_profile(client: AsyncClient):
    token, _ = await register_verified_user(client, "p@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/v1/panel/profile-setting", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "p@aiacademy.tj"

    r = await client.put(
        "/api/v1/panel/profile-setting",
        headers=headers,
        json={"bio": "hello", "newsletter": True, "level_of_training": ["beginner", "expert"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bio"] == "hello"
    assert body["newsletter"] is True
    assert body["level_of_training"] == 5  # beginner(1) + expert(4)


async def test_change_password(client: AsyncClient):
    token, _ = await register_verified_user(client, "q@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.put(
        "/api/v1/panel/profile-setting/password",
        headers=headers,
        json={"current_password": "Secret123!", "new_password": "Brandnew123!"},
    )
    assert r.status_code == 200
    assert r.json()["token"]

    r = await client.put(
        "/api/v1/panel/profile-setting/password",
        headers=headers,
        json={"current_password": "WRONG", "new_password": "Another123!"},
    )
    assert r.status_code == 403


async def test_profile_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/panel/profile-setting")
    assert r.status_code == 401
