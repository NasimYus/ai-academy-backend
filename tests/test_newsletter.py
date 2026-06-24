from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.newsletter import Newsletter
from app.models.user import User
from tests.conftest import register_verified_user


async def test_guest_subscribe_then_duplicate(client: AsyncClient):
    r = await client.post("/api/v1/newsletter", json={"email": "guest@aiacademy.tj"})
    assert r.status_code == 200
    assert r.json()["message"] == "subscribed_newsletter"

    # second time the same email is rejected (legacy unique validation)
    dup = await client.post("/api/v1/newsletter", json={"email": "guest@aiacademy.tj"})
    assert dup.status_code == 422
    assert dup.json()["detail"] == "already_subscribed"


async def test_authed_own_email_flags_user(client: AsyncClient):
    token, user_id = await register_verified_user(client, email="me@aiacademy.tj")
    r = await client.post(
        "/api/v1/newsletter",
        json={"email": "me@aiacademy.tj"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        assert user.newsletter is True
        row = (
            await db.execute(select(Newsletter).where(Newsletter.email == "me@aiacademy.tj"))
        ).scalar_one()
        assert row.user_id == user_id


async def test_authed_other_email_not_linked(client: AsyncClient):
    token, user_id = await register_verified_user(client, email="owner@aiacademy.tj")
    r = await client.post(
        "/api/v1/newsletter",
        json={"email": "someone-else@aiacademy.tj"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        assert user.newsletter is False
        row = (
            await db.execute(
                select(Newsletter).where(Newsletter.email == "someone-else@aiacademy.tj")
            )
        ).scalar_one()
        assert row.user_id is None
