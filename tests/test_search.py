from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.course import Course, CourseStatus, CourseType


async def _seed_courses() -> None:
    async with AsyncSessionLocal() as db:
        cat = Category(title="Programming", slug="prog", order=1)
        db.add(cat)
        await db.flush()
        db.add_all(
            [
                Course(
                    title="Python Basics",
                    slug="python-basics",
                    type=CourseType.course,
                    status=CourseStatus.active,
                    price=0,
                    category_id=cat.id,
                ),
                Course(
                    title="Advanced JS",
                    slug="advanced-js",
                    type=CourseType.webinar,
                    status=CourseStatus.active,
                    price=200,
                    downloadable=True,
                ),
                Course(
                    title="Draft Course",
                    slug="draft",
                    type=CourseType.course,
                    status=CourseStatus.is_draft,
                    price=10,
                ),
                Course(
                    title="Secret",
                    slug="secret",
                    type=CourseType.course,
                    status=CourseStatus.active,
                    price=0,
                    private=True,
                ),
            ]
        )
        await db.commit()


async def test_list_only_active_public(client: AsyncClient):
    await _seed_courses()
    r = await client.get("/api/v1/courses")
    assert r.status_code == 200
    slugs = {c["slug"] for c in r.json()}
    assert slugs == {"python-basics", "advanced-js"}  # draft + private hidden


async def test_filter_free(client: AsyncClient):
    await _seed_courses()
    r = await client.get("/api/v1/courses", params={"free": "true"})
    assert [c["slug"] for c in r.json()] == ["python-basics"]


async def test_filter_type_and_downloadable(client: AsyncClient):
    await _seed_courses()
    r = await client.get("/api/v1/courses", params={"type": "webinar"})
    assert [c["slug"] for c in r.json()] == ["advanced-js"]
    r = await client.get("/api/v1/courses", params={"downloadable": "true"})
    assert [c["slug"] for c in r.json()] == ["advanced-js"]


async def test_filter_category_and_sort(client: AsyncClient):
    await _seed_courses()
    r = await client.get("/api/v1/courses", params={"sort": "expensive"})
    assert [c["slug"] for c in r.json()][0] == "advanced-js"  # 200 first
    r = await client.get("/api/v1/courses", params={"sort": "cheapest"})
    assert [c["slug"] for c in r.json()][0] == "python-basics"  # 0 first


async def test_search_courses_and_short_query(client: AsyncClient):
    await _seed_courses()
    r = await client.get("/api/v1/search", params={"search": "python"})
    assert r.status_code == 200
    body = r.json()
    assert body["webinars"]["count"] == 1
    assert body["webinars"]["webinars"][0]["slug"] == "python-basics"

    # too short -> empty groups
    r = await client.get("/api/v1/search", params={"search": "py"})
    assert r.json()["webinars"]["count"] == 0
