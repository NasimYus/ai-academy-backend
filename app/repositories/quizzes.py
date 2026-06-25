from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quiz import Quiz as QuizModel
from app.models.quiz import (
    QuizQuestion,
    QuizQuestionAnswer,
    QuizResult,
    QuizStatus,
    ResultStatus,
)


async def get_by_id(db: AsyncSession, quiz_id: int) -> QuizModel | None:
    return await db.get(QuizModel, quiz_id)


# --- instructor management (Phase 6.2) ---


async def get_owned(db: AsyncSession, quiz_id: int, creator_id: int) -> QuizModel | None:
    """A quiz created by the given user (legacy creator_id scope)."""
    result = await db.execute(
        select(QuizModel).where(QuizModel.id == quiz_id, QuizModel.creator_id == creator_id)
    )
    return result.scalar_one_or_none()


async def list_by_creator(db: AsyncSession, creator_id: int) -> list[QuizModel]:
    """All quizzes the instructor created (newest first)."""
    result = await db.execute(
        select(QuizModel)
        .where(QuizModel.creator_id == creator_id)
        .order_by(QuizModel.created_at.desc())
    )
    return list(result.scalars().all())


async def create_quiz(db: AsyncSession, quiz: QuizModel) -> QuizModel:
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)
    return quiz


async def update_quiz(db: AsyncSession, quiz: QuizModel, changes: dict) -> QuizModel:
    for key, value in changes.items():
        setattr(quiz, key, value)
    await db.commit()
    await db.refresh(quiz)
    return quiz


async def delete_quiz(db: AsyncSession, quiz: QuizModel) -> None:
    await db.delete(quiz)
    await db.commit()


async def results_for_creator(db: AsyncSession, creator_id: int) -> list[QuizResult]:
    """Every attempt on the instructor's quizzes (quiz + student eager-loaded)."""
    quiz_ids = select(QuizModel.id).where(QuizModel.creator_id == creator_id)
    result = await db.execute(
        select(QuizResult)
        .where(QuizResult.quiz_id.in_(quiz_ids))
        .options(selectinload(QuizResult.quiz), selectinload(QuizResult.user))
        .order_by(QuizResult.created_at.desc())
    )
    return list(result.scalars().all())


async def get_active(db: AsyncSession, quiz_id: int) -> QuizModel | None:
    result = await db.execute(
        select(QuizModel).where(QuizModel.id == quiz_id, QuizModel.status == QuizStatus.active)
    )
    return result.scalar_one_or_none()


async def active_for_course(db: AsyncSession, course_id: int) -> list[QuizModel]:
    result = await db.execute(
        select(QuizModel)
        .where(QuizModel.course_id == course_id, QuizModel.status == QuizStatus.active)
        .order_by(QuizModel.created_at.desc())
    )
    return list(result.scalars().all())


async def questions_with_answers(db: AsyncSession, quiz_id: int) -> list[QuizQuestion]:
    result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz_id)
        .options(selectinload(QuizQuestion.answers))
        .order_by(QuizQuestion.order.asc().nullslast(), QuizQuestion.id.asc())
    )
    return list(result.scalars().all())


async def get_question(db: AsyncSession, question_id: int, quiz_id: int) -> QuizQuestion | None:
    result = await db.execute(
        select(QuizQuestion).where(QuizQuestion.id == question_id, QuizQuestion.quiz_id == quiz_id)
    )
    return result.scalar_one_or_none()


async def find_answer(
    db: AsyncSession, answer_id: int, question_id: int, creator_id: int | None
) -> QuizQuestionAnswer | None:
    """Legacy looks the answer up scoped to the quiz creator."""
    stmt = select(QuizQuestionAnswer).where(
        QuizQuestionAnswer.id == answer_id, QuizQuestionAnswer.question_id == question_id
    )
    if creator_id is not None:
        stmt = stmt.where(QuizQuestionAnswer.creator_id == creator_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def user_results(db: AsyncSession, quiz_id: int, user_id: int) -> list[QuizResult]:
    """All of a user's attempts for a quiz, newest first."""
    result = await db.execute(
        select(QuizResult)
        .where(QuizResult.quiz_id == quiz_id, QuizResult.user_id == user_id)
        .order_by(QuizResult.id.desc())
    )
    return list(result.scalars().all())


async def passed_results_for_user(db: AsyncSession, user_id: int) -> list[QuizResult]:
    """A user's passed attempts on active quizzes (legacy achievements), quiz loaded."""
    result = await db.execute(
        select(QuizResult)
        .join(QuizModel, QuizModel.id == QuizResult.quiz_id)
        .where(
            QuizResult.user_id == user_id,
            QuizResult.status == ResultStatus.passed,
            QuizModel.status == QuizStatus.active,
        )
        .options(selectinload(QuizResult.quiz))
        .order_by(QuizResult.id.desc())
    )
    return list(result.scalars().all())


async def count_results(db: AsyncSession, quiz_id: int, user_id: int) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(QuizResult)
        .where(QuizResult.quiz_id == quiz_id, QuizResult.user_id == user_id)
    )
    return int(result.scalar_one())


async def get_result(db: AsyncSession, result_id: int) -> QuizResult | None:
    return await db.get(QuizResult, result_id)


async def get_user_result(db: AsyncSession, result_id: int, user_id: int) -> QuizResult | None:
    result = await db.execute(
        select(QuizResult).where(QuizResult.id == result_id, QuizResult.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def result_for_quiz(db: AsyncSession, quiz_id: int, user_id: int) -> QuizResult | None:
    """A passed attempt if any, else the latest attempt (legacy resultsByQuiz)."""
    passed = await db.execute(
        select(QuizResult)
        .where(
            QuizResult.quiz_id == quiz_id,
            QuizResult.user_id == user_id,
            QuizResult.status == ResultStatus.passed,
        )
        .order_by(QuizResult.id.desc())
    )
    row = passed.scalars().first()
    if row is not None:
        return row
    latest = await db.execute(
        select(QuizResult)
        .where(QuizResult.quiz_id == quiz_id, QuizResult.user_id == user_id)
        .order_by(QuizResult.id.desc())
    )
    return latest.scalars().first()


async def create_result(
    db: AsyncSession, *, quiz_id: int, user_id: int, status: ResultStatus
) -> QuizResult:
    row = QuizResult(quiz_id=quiz_id, user_id=user_id, results=None, user_grade=0, status=status)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
