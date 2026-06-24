from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.discount import (
    Discount,
    DiscountCourse,
    DiscountSource,
    DiscountType,
    DiscountUserType,
)
from tests.conftest import register_verified_user


async def _make_course(slug: str, price: float, category_id: int | None = None) -> int:
    async with AsyncSessionLocal() as db:
        course = Course(
            title=slug,
            slug=slug,
            type=CourseType.course,
            status=CourseStatus.active,
            price=price,
            category_id=category_id,
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course.id


async def _make_discount(**kwargs) -> int:
    defaults = dict(
        title="Coupon",
        code="SAVE",
        discount_type=DiscountType.percentage,
        source=DiscountSource.all,
        user_type=DiscountUserType.all_users,
        count=10,
        expired_at=datetime.now(UTC) + timedelta(days=30),
    )
    defaults.update(kwargs)
    async with AsyncSessionLocal() as db:
        d = Discount(**defaults)
        db.add(d)
        await db.commit()
        await db.refresh(d)
        return d.id


async def _auth(client: AsyncClient, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    return {"Authorization": f"Bearer {token}"}


async def _add(client: AsyncClient, headers: dict, course_id: int) -> None:
    await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": course_id, "item_name": "webinar"}
    )


async def test_percentage_all_source(client: AsyncClient):
    headers = await _auth(client, "cp1@aiacademy.tj")
    c = await _make_course("cp-course-1", 200)
    await _add(client, headers, c)
    await _make_discount(code="P20", percent=20, discount_type=DiscountType.percentage)

    r = await client.post("/api/v1/cart/coupon/validate", headers=headers, json={"coupon": "P20"})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["amounts"]["sub_total"] == 200
    assert body["amounts"]["total_discount"] == 40  # 20%
    assert body["amounts"]["total"] == 160


async def test_fixed_amount_capped_at_subtotal(client: AsyncClient):
    headers = await _auth(client, "cp2@aiacademy.tj")
    c = await _make_course("cp-course-2", 50)
    await _add(client, headers, c)
    await _make_discount(code="FIX100", discount_type=DiscountType.fixed_amount, amount=100)

    r = await client.post(
        "/api/v1/cart/coupon/validate", headers=headers, json={"coupon": "FIX100"}
    )
    body = r.json()
    assert body["valid"] is True
    # fixed 100 but subtotal 50 -> discount capped at 50
    assert body["amounts"]["total_discount"] == 50
    assert body["amounts"]["total"] == 0


async def test_percentage_max_amount_cap(client: AsyncClient):
    headers = await _auth(client, "cp3@aiacademy.tj")
    c = await _make_course("cp-course-3", 1000)
    await _add(client, headers, c)
    await _make_discount(code="P50CAP", percent=50, max_amount=100)

    r = await client.post(
        "/api/v1/cart/coupon/validate", headers=headers, json={"coupon": "P50CAP"}
    )
    body = r.json()
    assert body["amounts"]["total_discount"] == 100  # 50% of 1000 = 500, capped at 100


async def test_invalid_code(client: AsyncClient):
    headers = await _auth(client, "cp4@aiacademy.tj")
    r = await client.post("/api/v1/cart/coupon/validate", headers=headers, json={"coupon": "NOPE"})
    assert r.json() == {"valid": False, "message": "invalid", "amounts": None, "discount": None}


async def test_expired(client: AsyncClient):
    headers = await _auth(client, "cp5@aiacademy.tj")
    c = await _make_course("cp-course-5", 100)
    await _add(client, headers, c)
    await _make_discount(code="OLD", percent=10, expired_at=datetime.now(UTC) - timedelta(days=1))
    r = await client.post("/api/v1/cart/coupon/validate", headers=headers, json={"coupon": "OLD"})
    assert r.json()["valid"] is False
    assert r.json()["message"] == "expired"


async def test_minimum_order_not_met(client: AsyncClient):
    headers = await _auth(client, "cp6@aiacademy.tj")
    c = await _make_course("cp-course-6", 100)
    await _add(client, headers, c)
    await _make_discount(code="MIN500", percent=10, minimum_order=500)
    r = await client.post(
        "/api/v1/cart/coupon/validate", headers=headers, json={"coupon": "MIN500"}
    )
    assert r.json()["valid"] is False
    assert r.json()["message"] == "min_order"


async def test_course_scoped_wrong_course(client: AsyncClient):
    headers = await _auth(client, "cp7@aiacademy.tj")
    in_cart = await _make_course("cp-in-cart", 100)
    other = await _make_course("cp-other", 100)
    await _add(client, headers, in_cart)
    did = await _make_discount(code="CONLY", percent=10, source=DiscountSource.course)
    async with AsyncSessionLocal() as db:
        db.add(DiscountCourse(discount_id=did, course_id=other))
        await db.commit()

    r = await client.post("/api/v1/cart/coupon/validate", headers=headers, json={"coupon": "CONLY"})
    assert r.json()["valid"] is False
    assert r.json()["message"] == "wrong_course"


async def test_course_scoped_match(client: AsyncClient):
    headers = await _auth(client, "cp8@aiacademy.tj")
    c = await _make_course("cp-scoped-ok", 300)
    await _add(client, headers, c)
    did = await _make_discount(code="CMATCH", percent=10, source=DiscountSource.course)
    async with AsyncSessionLocal() as db:
        db.add(DiscountCourse(discount_id=did, course_id=c))
        await db.commit()

    r = await client.post(
        "/api/v1/cart/coupon/validate", headers=headers, json={"coupon": "CMATCH"}
    )
    body = r.json()
    assert body["valid"] is True
    assert body["amounts"]["total_discount"] == 30


async def test_empty_cart(client: AsyncClient):
    headers = await _auth(client, "cp9@aiacademy.tj")
    await _make_discount(code="ANY", percent=10)
    r = await client.post("/api/v1/cart/coupon/validate", headers=headers, json={"coupon": "ANY"})
    # source=all with empty cart: legacy still computes (cart empty -> invalid is_empty)
    assert r.json()["valid"] is False
    assert r.json()["message"] == "cart_empty"


async def test_requires_auth(client: AsyncClient):
    r = await client.post("/api/v1/cart/coupon/validate", json={"coupon": "X"})
    assert r.status_code == 401
