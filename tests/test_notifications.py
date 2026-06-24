from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.notification import Notification, NotificationType
from tests.conftest import register_verified_user


async def _seed(**kw) -> int:
    async with AsyncSessionLocal() as db:
        n = Notification(**kw)
        db.add(n)
        await db.commit()
        return n.id


async def test_list_includes_personal_and_broadcast(client: AsyncClient):
    token, user_id = await register_verified_user(client)
    _, other_id = await register_verified_user(client, email="other@aiacademy.tj")
    personal = await _seed(
        user_id=user_id, title="Hi", message="personal", type=NotificationType.single
    )
    broadcast = await _seed(title="All", message="everyone", type=NotificationType.all_users)
    students = await _seed(title="Stu", message="students", type=NotificationType.students)
    # addressed to another user -> must not appear
    await _seed(user_id=other_id, title="X", message="x", type=NotificationType.single)
    # a role bucket the user is not in
    await _seed(title="Ins", message="instructors", type=NotificationType.instructors)

    r = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    ids = {n["id"] for n in body["notifications"]}
    assert ids == {personal, broadcast, students}
    assert body["count"] == 3
    assert all(n["status"] == "unread" for n in body["notifications"])


async def test_seen_then_read_unread_filters(client: AsyncClient):
    token, user_id = await register_verified_user(client)
    a = await _seed(title="A", message="a", type=NotificationType.all_users)
    b = await _seed(title="B", message="b", type=NotificationType.all_users)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/api/v1/notifications/{a}/seen", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "seen"

    # marking again is idempotent
    r = await client.post(f"/api/v1/notifications/{a}/seen", headers=headers)
    assert r.json()["status"] == "already_seen"

    unread = await client.get("/api/v1/notifications?status=unread", headers=headers)
    assert {n["id"] for n in unread.json()["notifications"]} == {b}

    read = await client.get("/api/v1/notifications?status=read", headers=headers)
    assert {n["id"] for n in read.json()["notifications"]} == {a}


async def test_seen_unknown_or_foreign_404(client: AsyncClient):
    token, user_id = await register_verified_user(client)
    _, other_id = await register_verified_user(client, email="other@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    # not visible to this user (personal to someone else)
    foreign = await _seed(
        user_id=other_id, title="F", message="f", type=NotificationType.single
    )
    assert (
        await client.post(f"/api/v1/notifications/{foreign}/seen", headers=headers)
    ).status_code == 404
    assert (
        await client.post("/api/v1/notifications/999999/seen", headers=headers)
    ).status_code == 404


async def test_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/notifications")).status_code == 401
