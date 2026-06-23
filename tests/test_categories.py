from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.category import Category, TrendCategory


async def _seed_categories() -> None:
    async with AsyncSessionLocal() as db:
        prog = Category(title="Programming", slug="prog", order=1)
        db.add(prog)
        await db.flush()
        db.add_all(
            [
                Category(title="Python", parent_id=prog.id, order=1),
                Category(title="Hidden", parent_id=prog.id, order=2, enable=False),
                TrendCategory(category_id=prog.id, color="#abc", icon="/i.svg"),
            ]
        )
        await db.commit()


async def test_list_categories(client: AsyncClient):
    await _seed_categories()
    r = await client.get("/api/v1/categories")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    top = body["categories"][0]
    assert top["title"] == "Programming"
    assert top["color"] == "#abc"
    # disabled sub-category is excluded
    assert [s["title"] for s in top["sub_categories"]] == ["Python"]


async def test_list_trend_categories(client: AsyncClient):
    await _seed_categories()
    r = await client.get("/api/v1/trend-categories")
    assert r.status_code == 200
    assert r.json()["count"] == 1
    assert r.json()["categories"][0]["color"] == "#abc"


async def test_empty_categories(client: AsyncClient):
    r = await client.get("/api/v1/categories")
    assert r.status_code == 200
    assert r.json() == {"count": 0, "categories": []}
