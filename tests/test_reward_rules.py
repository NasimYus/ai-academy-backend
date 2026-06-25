import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment, EnrollmentSource
from app.models.quiz import QuestionType, Quiz, QuizQuestion, QuizQuestionAnswer, QuizStatus
from app.models.reward import Reward, RewardAccounting, RewardStatus, RewardType
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


@pytest.fixture
def rewards_on(monkeypatch):
    monkeypatch.setattr(settings, "rewards_status", True)


async def _seed_rule(reward_type: RewardType, *, score: int = 10, condition: str | None = None):
    async with AsyncSessionLocal() as db:
        db.add(Reward(type=reward_type, score=score, condition=condition, enabled=True))
        await db.commit()


async def _earned(user_id: int) -> int:
    async with AsyncSessionLocal() as db:
        total = await db.execute(
            select(func.coalesce(func.sum(RewardAccounting.score), 0)).where(
                RewardAccounting.user_id == user_id,
                RewardAccounting.status == RewardStatus.addiction,
            )
        )
        return int(total.scalar_one())


async def test_register_awards_points(client, rewards_on):
    await _seed_rule(RewardType.register, score=25)
    _, user_id = await register_verified_user(client, email="newbie@aiacademy.tj")
    assert await _earned(user_id) == 25


async def test_register_no_points_when_gate_off(client):
    await _seed_rule(RewardType.register, score=25)
    _, user_id = await register_verified_user(client, email="newbie@aiacademy.tj")
    assert await _earned(user_id) == 0


async def test_register_no_points_without_rule(client, rewards_on):
    _, user_id = await register_verified_user(client, email="newbie@aiacademy.tj")
    assert await _earned(user_id) == 0


async def test_newsletter_awards_once(client, rewards_on):
    await _seed_rule(RewardType.newsletters, score=5)
    token, user_id = await register_verified_user(client, email="me@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/newsletter", json={"email": "me@aiacademy.tj"}, headers=headers)
    assert r.status_code == 200
    # register(0 rule) + newsletter(5)
    assert await _earned(user_id) == 5


async def test_award_for_dedup(client, rewards_on):
    from app.services import rewards as rewards_service

    await _seed_rule(RewardType.pass_the_quiz, score=15)
    _, user_id = await register_verified_user(client)
    async with AsyncSessionLocal() as db:
        for _ in range(2):
            await rewards_service.award_for(
                db,
                user_id=user_id,
                reward_type=RewardType.pass_the_quiz,
                item_id=42,
                check_duplicate=True,
            )
    assert await _earned(user_id) == 15  # second call de-duplicated


async def test_award_proportional_to_amount(client, rewards_on):
    from app.services import rewards as rewards_service

    # buy: score 1 per `condition` (10) units of amount
    await _seed_rule(RewardType.buy, score=1, condition="10")
    _, user_id = await register_verified_user(client)
    async with AsyncSessionLocal() as db:
        await rewards_service.award_for(
            db, user_id=user_id, reward_type=RewardType.buy, amount=100
        )
    assert await _earned(user_id) == 10  # 1 * (100 / 10)


async def _seed_passing_quiz() -> dict:
    async with AsyncSessionLocal() as db:
        teacher = User(
            full_name="T", email="t@aiacademy.tj", password="x", role_id=4, role_name=Role.TEACHER
        )
        db.add(teacher)
        await db.flush()
        course = Course(
            title="C", slug="c", type=CourseType.course, status=CourseStatus.active, price=0
        )
        db.add(course)
        await db.flush()
        quiz = Quiz(
            course_id=course.id,
            creator_id=teacher.id,
            title="Q",
            time=0,
            pass_mark=10,
            status=QuizStatus.active,
            total_mark=10,
        )
        db.add(quiz)
        await db.flush()
        q = QuizQuestion(
            quiz_id=quiz.id,
            creator_id=teacher.id,
            title="2+2",
            grade=10,
            type=QuestionType.multiple,
        )
        db.add(q)
        await db.flush()
        a_ok = QuizQuestionAnswer(question_id=q.id, creator_id=teacher.id, title="4", correct=True)
        a_no = QuizQuestionAnswer(question_id=q.id, creator_id=teacher.id, title="5", correct=False)
        db.add_all([a_ok, a_no])
        await db.commit()
        return {
            "quiz_id": quiz.id,
            "course_id": course.id,
            "question_id": q.id,
            "answer_id": a_ok.id,
        }


async def _enroll(user_id: int, course_id: int) -> None:
    async with AsyncSessionLocal() as db:
        db.add(Enrollment(user_id=user_id, course_id=course_id, source=EnrollmentSource.free))
        await db.commit()


async def test_pass_quiz_awards_once(client, rewards_on):
    await _seed_rule(RewardType.pass_the_quiz, score=15)
    ids = await _seed_passing_quiz()
    token, user_id = await register_verified_user(client, email="student@aiacademy.tj")
    await _enroll(user_id, ids["course_id"])
    headers = {"Authorization": f"Bearer {token}"}

    start = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}/start", headers=headers)
    result_id = start.json()["quiz_result_id"]
    body = {
        "quiz_result_id": result_id,
        "answer_sheet": [{"question_id": ids["question_id"], "answer": ids["answer_id"]}],
    }
    store = await client.post(
        f"/api/v1/quizzes/{ids['quiz_id']}/store-result", json=body, headers=headers
    )
    assert store.status_code == 200
    assert store.json()["status"] == "passed"
    assert await _earned(user_id) == 15
