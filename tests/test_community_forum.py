from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.community_forum import ForumCategory
from tests.conftest import register_verified_user


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _category(title: str = "Общие") -> int:
    async with AsyncSessionLocal() as db:
        cat = ForumCategory(title=title, slug=title.lower(), order=0)
        db.add(cat)
        await db.commit()
        await db.refresh(cat)
        return cat.id


async def test_forum_categories_listed(client: AsyncClient):
    await _category("Помощь")
    r = await client.get("/api/v1/forums")
    assert r.status_code == 200
    assert any(c["title"] == "Помощь" for c in r.json())


async def test_topic_create_reply_and_detail(client: AsyncClient):
    forum_id = await _category()
    token, _ = await register_verified_user(client, email="forumuser@aiacademy.tj")

    created = await client.post(
        "/api/v1/forum-topics",
        json={"forum_id": forum_id, "title": "Как сдать проект?", "description": "Подскажите"},
        headers=_auth(token),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Как сдать проект?" and body["slug"]
    topic_id, slug = body["id"], body["slug"]

    # topics list in the category
    topics = await client.get(f"/api/v1/forums/{forum_id}/topics")
    assert any(t["id"] == topic_id for t in topics.json())

    # reply
    reply = await client.post(
        f"/api/v1/forum-topics/{topic_id}/posts",
        json={"description": "Загрузите на шаге 4"},
        headers=_auth(token),
    )
    assert reply.status_code == 201

    # detail shows the post
    detail = await client.get(f"/api/v1/forum-topics/{slug}")
    assert detail.status_code == 200
    assert len(detail.json()["posts"]) == 1
    assert detail.json()["posts"][0]["description"] == "Загрузите на шаге 4"

    # my topics + my posts
    mine = await client.get("/api/v1/panel/forums/topics", headers=_auth(token))
    assert any(t["id"] == topic_id for t in mine.json())
    posts = await client.get("/api/v1/panel/forums/posts", headers=_auth(token))
    assert posts.json()[0]["topic_title"] == "Как сдать проект?"


async def test_topic_requires_valid_forum(client: AsyncClient):
    token, _ = await register_verified_user(client, email="forumuser2@aiacademy.tj")
    r = await client.post(
        "/api/v1/forum-topics",
        json={"forum_id": 999999, "title": "x", "description": "y"},
        headers=_auth(token),
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "forum_not_found"


async def test_topic_detail_404(client: AsyncClient):
    r = await client.get("/api/v1/forum-topics/nope")
    assert r.status_code == 404
