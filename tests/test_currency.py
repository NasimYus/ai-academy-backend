from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.currency import Currency


async def _seed_course(price: float) -> str:
    async with AsyncSessionLocal() as db:
        course = Course(
            title="Cur Course",
            slug="cur-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=price,
        )
        db.add(course)
        await db.commit()
        return course.slug


async def _seed_currency(**kw) -> None:
    async with AsyncSessionLocal() as db:
        db.add(Currency(**kw))
        await db.commit()


async def test_list_currencies(client: AsyncClient):
    await _seed_currency(currency="EUR", currency_position="right", exchange_rate=0.9, order=1)
    r = await client.get("/api/v1/currencies")
    assert r.status_code == 200
    codes = {c["code"]: c for c in r.json()}
    assert codes["EUR"]["sign"] == "€"
    assert codes["EUR"]["exchange_rate"] == 0.9


async def test_course_price_converted(client: AsyncClient):
    slug = await _seed_course(100)
    await _seed_currency(
        currency="EUR", currency_position="right_with_space", currency_decimal=2, exchange_rate=0.9
    )
    r = await client.get(f"/api/v1/courses/{slug}?currency=EUR")
    body = r.json()
    assert body["price"] == 90.0  # 100 * 0.9
    assert body["currency"] == "EUR"
    assert "€" in body["price_string"]


async def test_course_price_default_when_no_currency(client: AsyncClient):
    slug = await _seed_course(100)
    r = await client.get(f"/api/v1/courses/{slug}")
    body = r.json()
    # default currency (no rows) -> identity conversion, code = configured default
    assert body["price"] == 100.0
    assert body["currency"] == "USD"


async def test_unknown_currency_falls_back(client: AsyncClient):
    slug = await _seed_course(100)
    r = await client.get(f"/api/v1/courses/{slug}?currency=ZZZ")
    body = r.json()
    assert body["price"] == 100.0  # unknown -> default (identity)
    assert body["currency"] == "USD"


async def test_course_price_converted_via_header(client: AsyncClient):
    slug = await _seed_course(100)
    await _seed_currency(currency="EUR", currency_decimal=2, exchange_rate=0.9)
    r = await client.get(f"/api/v1/courses/{slug}", headers={"X-Currency": "EUR"})
    body = r.json()
    assert body["price"] == 90.0
    assert body["currency"] == "EUR"


async def test_course_list_converted(client: AsyncClient):
    slug = await _seed_course(200)
    await _seed_currency(currency="EUR", exchange_rate=0.5)
    r = await client.get("/api/v1/courses?currency=EUR")
    prices = {c["slug"]: c for c in r.json()}
    assert prices[slug]["price"] == 100.0  # 200 * 0.5
    assert prices[slug]["currency"] == "EUR"
