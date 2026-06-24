from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.course import Course, CourseStatus, CourseType
from app.models.translation import CategoryTranslation, CourseTranslation


async def _seed_course() -> str:
    async with AsyncSessionLocal() as db:
        course = Course(
            title="Default Title",
            slug="i18n-course",
            description="Default description",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add(course)
        await db.flush()
        db.add(
            CourseTranslation(
                course_id=course.id,
                locale="ru",
                title="Русское название",
                description="Русское описание",
            )
        )
        await db.commit()
        return course.slug


async def _seed_category() -> int:
    async with AsyncSessionLocal() as db:
        cat = Category(title="Programming", parent_id=None, enable=True, order=1)
        db.add(cat)
        await db.flush()
        db.add(CategoryTranslation(category_id=cat.id, locale="ru", title="Программирование"))
        await db.commit()
        return cat.id


async def test_course_detail_localized_by_query(client: AsyncClient):
    slug = await _seed_course()
    r = await client.get(f"/api/v1/courses/{slug}?locale=ru")
    body = r.json()
    assert body["title"] == "Русское название"
    assert body["description"] == "Русское описание"


async def test_course_detail_falls_back_to_default(client: AsyncClient):
    slug = await _seed_course()
    # no ru translation requested -> base (default-locale) columns
    r = await client.get(f"/api/v1/courses/{slug}?locale=fr")
    body = r.json()
    assert body["title"] == "Default Title"
    assert body["description"] == "Default description"


async def test_course_detail_locale_via_accept_language(client: AsyncClient):
    slug = await _seed_course()
    r = await client.get(f"/api/v1/courses/{slug}", headers={"Accept-Language": "ru-RU,ru;q=0.9"})
    assert r.json()["title"] == "Русское название"


async def test_course_list_localized(client: AsyncClient):
    slug = await _seed_course()
    r = await client.get("/api/v1/courses?locale=ru")
    titles = {c["slug"]: c["title"] for c in r.json()}
    assert titles[slug] == "Русское название"


async def test_categories_localized(client: AsyncClient):
    await _seed_category()
    r = await client.get("/api/v1/categories?locale=ru")
    titles = [c["title"] for c in r.json()["categories"]]
    assert "Программирование" in titles

    # default locale -> base title
    r = await client.get("/api/v1/categories?locale=en")
    titles = [c["title"] for c in r.json()["categories"]]
    assert "Programming" in titles
