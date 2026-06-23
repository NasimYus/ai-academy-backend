from httpx import AsyncClient

from tests.conftest import register_verified_user


async def test_register_three_steps_then_login_and_me(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/register/step/1",
        json={
            "email": "a@aiacademy.tj",
            "password": "secret12345",
            "password_confirmation": "secret12345",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "stored"
    assert body["code"]  # surfaced in debug

    r = await client.post(
        "/api/v1/auth/register/step/2", json={"user_id": body["user_id"], "code": body["code"]}
    )
    assert r.status_code == 200

    r = await client.post(
        "/api/v1/auth/register/step/3",
        json={"user_id": body["user_id"], "full_name": "Alice A"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.post(
        "/api/v1/auth/login", json={"username": "a@aiacademy.tj", "password": "secret12345"}
    )
    assert r.status_code == 200
    assert r.json()["profile_completion"] == []

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["full_name"] == "Alice A"
    assert r.json()["role_name"] == "user"


async def test_register_step2_rejects_wrong_code(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/register/step/1",
        json={
            "email": "b@aiacademy.tj",
            "password": "secret12345",
            "password_confirmation": "secret12345",
        },
    )
    uid = r.json()["user_id"]
    r = await client.post("/api/v1/auth/register/step/2", json={"user_id": uid, "code": "00000"})
    assert r.status_code == 422


async def test_login_wrong_password(client: AsyncClient):
    await register_verified_user(client, "c@aiacademy.tj")
    r = await client.post(
        "/api/v1/auth/login", json={"username": "c@aiacademy.tj", "password": "WRONG"}
    )
    assert r.status_code == 401


async def test_login_pending_account_is_not_verified(client: AsyncClient):
    # step 1 only -> account is pending
    await client.post(
        "/api/v1/auth/register/step/1",
        json={
            "email": "d@aiacademy.tj",
            "password": "secret12345",
            "password_confirmation": "secret12345",
        },
    )
    r = await client.post(
        "/api/v1/auth/login", json={"username": "d@aiacademy.tj", "password": "secret12345"}
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "not_verified"


async def test_logout(client: AsyncClient):
    token, _ = await register_verified_user(client, "e@aiacademy.tj")
    r = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "logout"


async def test_forgot_then_reset_password(client: AsyncClient):
    await register_verified_user(client, "f@aiacademy.tj")
    r = await client.post("/api/v1/auth/forget-password", json={"email": "f@aiacademy.tj"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert token

    r = await client.post(
        f"/api/v1/auth/reset-password/{token}",
        json={
            "email": "f@aiacademy.tj",
            "password": "newpass123",
            "password_confirmation": "newpass123",
        },
    )
    assert r.json()["status"] == "reset"

    r = await client.post(
        "/api/v1/auth/login", json={"username": "f@aiacademy.tj", "password": "newpass123"}
    )
    assert r.status_code == 200


async def test_reset_password_unknown_token_is_benign(client: AsyncClient):
    await register_verified_user(client, "g@aiacademy.tj")
    r = await client.post(
        "/api/v1/auth/reset-password/NOPE",
        json={
            "email": "g@aiacademy.tj",
            "password": "newpass123",
            "password_confirmation": "newpass123",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "no_request"


async def test_oauth_google_new_then_login(client: AsyncClient):
    profile = {"email": "h@aiacademy.tj", "name": "H User", "id": "g-1"}
    r = await client.post("/api/v1/auth/google/callback", json=profile)
    assert r.json()["status"] == "registered"
    assert r.json()["token"] is None

    r = await client.post("/api/v1/auth/google/callback", json=profile)
    assert r.json()["status"] == "login"
    assert r.json()["token"]
