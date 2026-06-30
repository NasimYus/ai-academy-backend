from httpx import AsyncClient


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, email: str, account_type: str | None) -> str:
    body = {"email": email, "password": "secret12345", "password_confirmation": "secret12345"}
    if account_type is not None:
        body["account_type"] = account_type
    r = await client.post("/api/v1/auth/register/step/1", json=body)
    step1 = r.json()
    await client.post(
        "/api/v1/auth/register/step/2", json={"user_id": step1["user_id"], "code": step1["code"]}
    )
    r = await client.post(
        "/api/v1/auth/register/step/3",
        json={"user_id": step1["user_id"], "full_name": "Role Test"},
    )
    return r.json()["access_token"]


async def test_default_registration_is_student(client: AsyncClient):
    token = await _register(client, "role-student@aiacademy.tj", None)
    body = (await client.get("/api/v1/panel/dashboard", headers=_auth(token))).json()
    assert body["is_instructor"] is False


async def test_registering_as_teacher_sets_instructor_role(client: AsyncClient):
    token = await _register(client, "role-teacher@aiacademy.tj", "teacher")
    body = (await client.get("/api/v1/panel/dashboard", headers=_auth(token))).json()
    assert body["is_instructor"] is True


async def test_unknown_account_type_falls_back_to_student(client: AsyncClient):
    token = await _register(client, "role-bogus@aiacademy.tj", "wizard")
    body = (await client.get("/api/v1/panel/dashboard", headers=_auth(token))).json()
    assert body["is_instructor"] is False
