from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _promote(uid: int, role_name: str) -> None:
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = role_name
        await db.commit()


async def test_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/panel/become-instructor")).status_code == 401
    assert (await client.get("/api/v1/admin/become-instructors")).status_code == 401


async def test_student_has_no_request_initially(client: AsyncClient):
    token, _ = await register_verified_user(client, email="bi-none@aiacademy.tj")
    r = await client.get("/api/v1/panel/become-instructor", headers=_auth(token))
    assert r.status_code == 200
    assert r.json() is None


async def test_student_submits_request(client: AsyncClient):
    token, _ = await register_verified_user(client, email="bi-apply@aiacademy.tj")
    r = await client.post(
        "/api/v1/panel/become-instructor",
        headers=_auth(token),
        json={"role": "teacher", "occupations": [1, 2], "description": "Хочу преподавать"},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
    assert r.json()["occupations"] == [1, 2]

    current = (await client.get("/api/v1/panel/become-instructor", headers=_auth(token))).json()
    assert current["role"] == "teacher"


async def test_instructor_cannot_apply(client: AsyncClient):
    token, uid = await register_verified_user(client, email="bi-teacher@aiacademy.tj")
    await _promote(uid, Role.TEACHER)
    r = await client.post(
        "/api/v1/panel/become-instructor", headers=_auth(token), json={"role": "teacher"}
    )
    assert r.status_code == 409


async def test_admin_accept_flips_role(client: AsyncClient):
    student_token, student_uid = await register_verified_user(client, email="bi-cand@aiacademy.tj")
    await client.post(
        "/api/v1/panel/become-instructor",
        headers=_auth(student_token),
        json={"role": "teacher", "occupations": [], "description": "x"},
    )

    admin_token, admin_uid = await register_verified_user(client, email="bi-admin@aiacademy.tj")
    await _promote(admin_uid, Role.ADMIN)

    listing = (
        await client.get("/api/v1/admin/become-instructors", headers=_auth(admin_token))
    ).json()
    assert len(listing) == 1
    request_id = listing[0]["id"]

    r = await client.post(
        f"/api/v1/admin/become-instructors/{request_id}/accept", headers=_auth(admin_token)
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accept"

    # the applicant is now an instructor
    dash = (await client.get("/api/v1/panel/dashboard", headers=_auth(student_token))).json()
    assert dash["is_instructor"] is True
