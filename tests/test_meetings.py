from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _teacher(client: AsyncClient, email: str = "teacher@aiacademy.tj") -> tuple[str, int]:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return token, uid


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup_meeting(client: AsyncClient, token: str) -> int:
    """Configure the teacher's meeting + one slot; return the time id."""
    await client.put(
        "/api/v1/panel/meeting",
        json={"amount": 100, "disabled": False},
        headers=_auth(token),
    )
    r = await client.post(
        "/api/v1/panel/meeting/times",
        json={"day_label": "monday", "time": "10:00-11:00"},
        headers=_auth(token),
    )
    return r.json()["id"]


async def test_configure_meeting_and_slots(client: AsyncClient):
    token, _ = await _teacher(client)
    time_id = await _setup_meeting(client, token)
    assert time_id > 0

    r = await client.get("/api/v1/panel/meeting", headers=_auth(token))
    body = r.json()
    assert body["amount"] == 100
    assert body["disabled"] is False
    assert len(body["times"]) == 1
    assert body["times"][0]["day_label"] == "monday"


async def test_non_teacher_cannot_configure(client: AsyncClient):
    token, _ = await register_verified_user(client)
    r = await client.put("/api/v1/panel/meeting", json={"disabled": False}, headers=_auth(token))
    assert r.status_code == 403


async def test_public_instructor_meeting(client: AsyncClient):
    token, tid = await _teacher(client)
    await _setup_meeting(client, token)
    r = await client.get(f"/api/v1/users/{tid}/meeting")
    assert r.status_code == 200
    assert r.json()["times"][0]["time"] == "10:00-11:00"


async def test_reserve_and_buckets(client: AsyncClient):
    token, tid = await _teacher(client)
    time_id = await _setup_meeting(client, token)
    student_token, sid = await register_verified_user(client, email="stu@aiacademy.tj")

    r = await client.post(
        "/api/v1/meetings/reserve",
        json={"meeting_time_id": time_id, "description": "Need help with lesson 3"},
        headers=_auth(student_token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["amount"] == 100
    assert body["time"] == {"start": "10:00", "end": "11:00"}
    assert body["instructor"]["id"] == tid

    # student sees it under reservations
    mine = (await client.get("/api/v1/panel/meetings", headers=_auth(student_token))).json()
    assert mine["reservations"]["count"] == 1
    assert mine["requests"]["count"] == 0

    # teacher sees it under requests
    theirs = (await client.get("/api/v1/panel/meetings", headers=_auth(token))).json()
    assert theirs["requests"]["count"] == 1
    assert theirs["reservations"]["count"] == 0


async def test_cannot_reserve_own_meeting(client: AsyncClient):
    token, _ = await _teacher(client)
    time_id = await _setup_meeting(client, token)
    r = await client.post(
        "/api/v1/meetings/reserve", json={"meeting_time_id": time_id}, headers=_auth(token)
    )
    assert r.status_code == 400


async def test_finish_reservation(client: AsyncClient):
    token, tid = await _teacher(client)
    time_id = await _setup_meeting(client, token)
    student_token, _ = await register_verified_user(client, email="stu@aiacademy.tj")
    reserve_id = (
        await client.post(
            "/api/v1/meetings/reserve",
            json={"meeting_time_id": time_id},
            headers=_auth(student_token),
        )
    ).json()["id"]

    r = await client.post(f"/api/v1/panel/meetings/{reserve_id}/finish", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["status"] == "finished"


async def test_show_foreign_reservation_404(client: AsyncClient):
    token, _ = await _teacher(client)
    time_id = await _setup_meeting(client, token)
    student_token, _ = await register_verified_user(client, email="stu@aiacademy.tj")
    reserve_id = (
        await client.post(
            "/api/v1/meetings/reserve",
            json={"meeting_time_id": time_id},
            headers=_auth(student_token),
        )
    ).json()["id"]

    other_token, _ = await register_verified_user(client, email="other@aiacademy.tj")
    r = await client.get(f"/api/v1/panel/meetings/{reserve_id}", headers=_auth(other_token))
    assert r.status_code == 404


async def test_delete_slot_owned_and_foreign(client: AsyncClient):
    token, _ = await _teacher(client)
    time_id = await _setup_meeting(client, token)
    other_token, _ = await _teacher(client, email="other@aiacademy.tj")

    # foreign teacher can't delete my slot
    assert (
        await client.delete(f"/api/v1/panel/meeting/times/{time_id}", headers=_auth(other_token))
    ).status_code == 404
    # owner can
    assert (
        await client.delete(f"/api/v1/panel/meeting/times/{time_id}", headers=_auth(token))
    ).status_code == 204
