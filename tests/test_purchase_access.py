from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.payment import PaymentChannel, PaymentChannelStatus
from tests.conftest import register_verified_user


async def _make_course(slug: str, price: float) -> tuple[int, str]:
    async with AsyncSessionLocal() as db:
        course = Course(
            title=slug, slug=slug, type=CourseType.course, status=CourseStatus.active, price=price
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course.id, course.slug


async def _channel() -> int:
    async with AsyncSessionLocal() as db:
        ch = PaymentChannel(
            title="Sandbox", class_name="Sandbox", status=PaymentChannelStatus.active
        )
        db.add(ch)
        await db.commit()
        await db.refresh(ch)
        return ch.id


async def _auth(client: AsyncClient, email: str) -> dict:
    token, _ = await register_verified_user(client, email)
    return {"Authorization": f"Bearer {token}"}


async def _pay(client: AsyncClient, headers: dict, course_id: int, gid: int) -> None:
    await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": course_id, "item_name": "webinar"}
    )
    order_id = (await client.post("/api/v1/cart/checkout", headers=headers, json={})).json()["id"]
    await client.post(
        "/api/v1/payments/request", headers=headers, json={"order_id": order_id, "gateway_id": gid}
    )
    await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=headers,
        json={"order_id": order_id, "status": "success"},
    )


async def test_paid_order_grants_access(client: AsyncClient):
    headers = await _auth(client, "pa1@aiacademy.tj")
    gid = await _channel()
    course_id, slug = await _make_course("pa-course-1", 250)

    # before: no access
    r = await client.get(f"/api/v1/courses/{slug}", headers=headers)
    assert r.json()["auth_has_bought"] is False

    await _pay(client, headers, course_id, gid)

    # after paying: access granted
    r = await client.get(f"/api/v1/courses/{slug}", headers=headers)
    assert r.json()["auth_has_bought"] is True

    # appears in my-courses
    r = await client.get("/api/v1/panel/my-courses", headers=headers)
    slugs = [c["slug"] for c in r.json()]
    assert slug in slugs


async def test_failed_payment_no_access(client: AsyncClient):
    headers = await _auth(client, "pa2@aiacademy.tj")
    gid = await _channel()
    course_id, slug = await _make_course("pa-course-2", 100)

    await client.post(
        "/api/v1/cart", headers=headers, json={"item_id": course_id, "item_name": "webinar"}
    )
    order_id = (await client.post("/api/v1/cart/checkout", headers=headers, json={})).json()["id"]
    await client.post(
        "/api/v1/payments/request", headers=headers, json={"order_id": order_id, "gateway_id": gid}
    )
    await client.post(
        "/api/v1/payments/verify/Sandbox",
        headers=headers,
        json={"order_id": order_id, "status": "failed"},
    )

    r = await client.get(f"/api/v1/courses/{slug}", headers=headers)
    assert r.json()["auth_has_bought"] is False


async def test_my_courses_empty_then_listed(client: AsyncClient):
    headers = await _auth(client, "pa3@aiacademy.tj")
    r = await client.get("/api/v1/panel/my-courses", headers=headers)
    assert r.json() == []


async def test_my_courses_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/panel/my-courses")
    assert r.status_code == 401
