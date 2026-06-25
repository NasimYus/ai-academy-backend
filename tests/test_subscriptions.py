from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment
from app.models.subscription import Subscribe
from tests.conftest import register_verified_user


async def _seed_plan(*, price: float = 0, usable_count: int = 3, days: int = 30) -> int:
    async with AsyncSessionLocal() as db:
        plan = Subscribe(title="Monthly", usable_count=usable_count, days=days, price=price)
        db.add(plan)
        await db.commit()
        return plan.id


async def _seed_course(*, subscribe: bool = True, price: float = 100, slug: str = "sub-c") -> int:
    async with AsyncSessionLocal() as db:
        course = Course(
            title="Sub Course",
            slug=slug,
            type=CourseType.course,
            status=CourseStatus.active,
            price=price,
            subscribe=subscribe,
        )
        db.add(course)
        await db.commit()
        return course.id


async def _enrolled_count(user_id: int) -> int:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(Enrollment.__table__.select().where(Enrollment.user_id == user_id))
        ).all()
        return len(rows)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_list_plans_anonymous(client: AsyncClient):
    await _seed_plan()
    r = await client.get("/api/v1/subscribe")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["subscribed"] is None


async def test_activate_then_apply(client: AsyncClient):
    plan_id = await _seed_plan(usable_count=3)
    course_id = await _seed_course()
    token, user_id = await register_verified_user(client)

    act = await client.post(f"/api/v1/subscribe/{plan_id}/activate", headers=_auth(token))
    assert act.status_code == 200

    listed = await client.get("/api/v1/subscribe", headers=_auth(token))
    assert listed.json()["subscribed"]["remaining"] == 3

    applied = await client.post(
        "/api/v1/subscribe/apply", json={"course_id": course_id}, headers=_auth(token)
    )
    assert applied.status_code == 200
    assert applied.json()["message"] == "subscribed"
    assert await _enrolled_count(user_id) == 1

    after = await client.get("/api/v1/subscribe", headers=_auth(token))
    assert after.json()["subscribed"]["used_count"] == 1
    assert after.json()["subscribed"]["remaining"] == 2


async def test_apply_without_active_subscription(client: AsyncClient):
    course_id = await _seed_course()
    token, _ = await register_verified_user(client)
    r = await client.post(
        "/api/v1/subscribe/apply", json={"course_id": course_id}, headers=_auth(token)
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "no_active_subscribe"


async def test_apply_non_subscribable_course(client: AsyncClient):
    plan_id = await _seed_plan()
    course_id = await _seed_course(subscribe=False)
    token, _ = await register_verified_user(client)
    await client.post(f"/api/v1/subscribe/{plan_id}/activate", headers=_auth(token))
    r = await client.post(
        "/api/v1/subscribe/apply", json={"course_id": course_id}, headers=_auth(token)
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "not_subscribable"


async def test_activate_paid_plan_rejected(client: AsyncClient):
    plan_id = await _seed_plan(price=50)
    token, _ = await register_verified_user(client)
    r = await client.post(f"/api/v1/subscribe/{plan_id}/activate", headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "not_free"
