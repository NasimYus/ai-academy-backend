from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.bundle import Bundle, BundleStatus, BundleWebinar
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment
from app.models.reward import RewardAccounting, RewardStatus
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _seed_bundle(*, price: float | None = 0, points: int | None = None) -> dict:
    async with AsyncSessionLocal() as db:
        teacher = User(
            full_name="T", email="t@aiacademy.tj", password="x", role_id=4, role_name=Role.TEACHER
        )
        db.add(teacher)
        await db.flush()
        c1 = Course(
            title="C1", slug="c1", type=CourseType.course, status=CourseStatus.active, price=100
        )
        c2 = Course(
            title="C2", slug="c2", type=CourseType.course, status=CourseStatus.active, price=100
        )
        db.add_all([c1, c2])
        await db.flush()
        bundle = Bundle(
            creator_id=teacher.id,
            teacher_id=teacher.id,
            title="Bundle",
            slug="bundle",
            price=price,
            points=points,
            status=BundleStatus.active,
        )
        db.add(bundle)
        await db.flush()
        db.add_all(
            [
                BundleWebinar(bundle_id=bundle.id, course_id=c1.id, order=1),
                BundleWebinar(bundle_id=bundle.id, course_id=c2.id, order=2),
            ]
        )
        await db.commit()
        return {"bundle_id": bundle.id, "course_ids": [c1.id, c2.id]}


async def _give_points(user_id: int, score: int) -> None:
    async with AsyncSessionLocal() as db:
        db.add(
            RewardAccounting(
                user_id=user_id, score=score, type="buy", status=RewardStatus.addiction
            )
        )
        await db.commit()


async def _enrolled_count(user_id: int) -> int:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(Enrollment.__table__.select().where(Enrollment.user_id == user_id))
        ).all()
        return len(rows)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_list_and_show_bundle(client: AsyncClient):
    ids = await _seed_bundle()
    r = await client.get("/api/v1/bundles")
    assert r.status_code == 200
    assert [b["id"] for b in r.json()] == [ids["bundle_id"]]
    assert r.json()[0]["webinars_count"] == 2

    detail = await client.get(f"/api/v1/bundles/{ids['bundle_id']}")
    assert detail.status_code == 200
    assert [c["slug"] for c in detail.json()["courses"]] == ["c1", "c2"]


async def test_free_bundle_enrolls_all_courses(client: AsyncClient):
    ids = await _seed_bundle(price=0)
    token, user_id = await register_verified_user(client)
    r = await client.post(f"/api/v1/bundles/{ids['bundle_id']}/free", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["message"] == "enrolled"
    assert await _enrolled_count(user_id) == 2

    # buying again → nothing left to grant
    again = await client.post(f"/api/v1/bundles/{ids['bundle_id']}/free", headers=_auth(token))
    assert again.status_code == 422
    assert again.json()["detail"] == "already_purchased"


async def test_free_rejects_paid_bundle(client: AsyncClient):
    ids = await _seed_bundle(price=200)
    token, _ = await register_verified_user(client)
    r = await client.post(f"/api/v1/bundles/{ids['bundle_id']}/free", headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "not_free"


async def test_buy_with_points(client: AsyncClient):
    ids = await _seed_bundle(price=200, points=50)
    token, user_id = await register_verified_user(client)
    await _give_points(user_id, 80)

    r = await client.post(f"/api/v1/bundles/{ids['bundle_id']}/buyWithPoint", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["message"] == "paid"
    assert await _enrolled_count(user_id) == 2


async def test_buy_with_points_not_enough(client: AsyncClient):
    ids = await _seed_bundle(price=200, points=50)
    token, user_id = await register_verified_user(client)
    await _give_points(user_id, 10)
    r = await client.post(f"/api/v1/bundles/{ids['bundle_id']}/buyWithPoint", headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "no_enough_points"


async def test_buy_with_points_no_points_bundle(client: AsyncClient):
    ids = await _seed_bundle(price=200, points=None)
    token, _ = await register_verified_user(client)
    r = await client.post(f"/api/v1/bundles/{ids['bundle_id']}/buyWithPoint", headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "no_points"
