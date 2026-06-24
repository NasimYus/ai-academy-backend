import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment, EnrollmentSource
from app.models.reward import RewardAccounting, RewardStatus
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


@pytest.fixture
def rewards_on(monkeypatch):
    monkeypatch.setattr(settings, "rewards_status", True)


async def _seed_points(user_id: int, *, addiction: int = 0, deduction: int = 0) -> None:
    async with AsyncSessionLocal() as db:
        if addiction:
            db.add(
                RewardAccounting(
                    user_id=user_id, score=addiction, type="buy", status=RewardStatus.addiction
                )
            )
        if deduction:
            db.add(
                RewardAccounting(
                    user_id=user_id,
                    score=deduction,
                    type="withdraw",
                    status=RewardStatus.deduction,
                )
            )
        await db.commit()


async def _seed_course(*, points: int | None = 50, price: float = 100) -> int:
    async with AsyncSessionLocal() as db:
        teacher = User(
            full_name="T", email="t@aiacademy.tj", password="x", role_id=4, role_name=Role.TEACHER
        )
        db.add(teacher)
        await db.flush()
        course = Course(
            title="Reward Course",
            slug="reward-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=price,
            points=points,
            creator_id=teacher.id,
        )
        db.add(course)
        await db.commit()
        return course.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_overview_gated_off_returns_404(client: AsyncClient):
    token, _ = await register_verified_user(client)
    r = await client.get("/api/v1/rewards", headers=_auth(token))
    assert r.status_code == 404


async def test_overview_when_enabled(client: AsyncClient, rewards_on):
    token, user_id = await register_verified_user(client)
    await _seed_points(user_id, addiction=100, deduction=30)
    r = await client.get("/api/v1/rewards", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total_points"] == 100
    assert body["spent_points"] == 30
    assert body["available_points"] == 70
    assert len(body["rewards"]) == 2
    assert body["leader_board"]["total_points"] == 100


async def test_reward_courses_ungated(client: AsyncClient):
    await _seed_course(points=50)
    r = await client.get("/api/v1/rewards/reward-courses")
    assert r.status_code == 200
    body = r.json()
    assert [c["slug"] for c in body] == ["reward-course"]


async def test_exchange_gated_off_returns_403(client: AsyncClient):
    token, _ = await register_verified_user(client)
    r = await client.post("/api/v1/rewards/exchange", headers=_auth(token))
    assert r.status_code == 403


async def test_buy_with_points_success(client: AsyncClient):
    course_id = await _seed_course(points=50, price=100)
    token, user_id = await register_verified_user(client)
    await _seed_points(user_id, addiction=80)

    r = await client.post(f"/api/v1/rewards/webinar/{course_id}/apply", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["message"] == "paid"

    async with AsyncSessionLocal() as db:
        enrollment = (
            await db.execute(Enrollment.__table__.select().where(Enrollment.user_id == user_id))
        ).first()
        assert enrollment is not None
        assert enrollment.source == EnrollmentSource.reward.value
        # 80 earned - 50 spent = 30 available
        spent = (
            await db.execute(
                RewardAccounting.__table__.select().where(
                    RewardAccounting.user_id == user_id,
                    RewardAccounting.status == RewardStatus.deduction,
                )
            )
        ).first()
        assert spent is not None


async def test_buy_with_points_not_enough(client: AsyncClient):
    course_id = await _seed_course(points=50, price=100)
    token, user_id = await register_verified_user(client)
    await _seed_points(user_id, addiction=10)
    r = await client.post(f"/api/v1/rewards/webinar/{course_id}/apply", headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "no_enough_points"


async def test_buy_with_points_free_course(client: AsyncClient):
    course_id = await _seed_course(points=50, price=0)
    token, _ = await register_verified_user(client)
    r = await client.post(f"/api/v1/rewards/webinar/{course_id}/apply", headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "free"
