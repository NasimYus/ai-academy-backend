from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import (
    Assignment,
    AssignmentHistory,
    AssignmentHistoryMessage,
    AssignmentStatus,
)


async def get_active(db: AsyncSession, assignment_id: int) -> Assignment | None:
    result = await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id, Assignment.status == AssignmentStatus.active
        )
    )
    return result.scalar_one_or_none()


async def active_for_course(db: AsyncSession, course_id: int) -> list[Assignment]:
    result = await db.execute(
        select(Assignment)
        .where(Assignment.course_id == course_id, Assignment.status == AssignmentStatus.active)
        .order_by(Assignment.order.asc(), Assignment.created_at.desc())
    )
    return list(result.scalars().all())


async def active_for_courses(db: AsyncSession, course_ids: list[int]) -> list[Assignment]:
    if not course_ids:
        return []
    result = await db.execute(
        select(Assignment)
        .where(Assignment.course_id.in_(course_ids), Assignment.status == AssignmentStatus.active)
        .order_by(Assignment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_history(
    db: AsyncSession, *, assignment_id: int, student_id: int
) -> AssignmentHistory | None:
    result = await db.execute(
        select(AssignmentHistory)
        .where(
            AssignmentHistory.assignment_id == assignment_id,
            AssignmentHistory.student_id == student_id,
        )
        .options(
            selectinload(AssignmentHistory.assignment),
            selectinload(AssignmentHistory.student),
        )
    )
    return result.scalar_one_or_none()


async def histories_for_student(
    db: AsyncSession, *, student_id: int, course_ids: list[int]
) -> list[AssignmentHistory]:
    """The student's submission threads across the given courses' active assignments."""
    if not course_ids:
        return []
    result = await db.execute(
        select(AssignmentHistory)
        .join(Assignment, Assignment.id == AssignmentHistory.assignment_id)
        .where(
            AssignmentHistory.student_id == student_id,
            Assignment.course_id.in_(course_ids),
            Assignment.status == AssignmentStatus.active,
        )
        .options(
            selectinload(AssignmentHistory.assignment),
            selectinload(AssignmentHistory.student),
        )
        .order_by(AssignmentHistory.created_at.desc())
    )
    return list(result.scalars().all())


async def create_history(
    db: AsyncSession, *, instructor_id: int, student_id: int, assignment_id: int, status
) -> AssignmentHistory:
    history = AssignmentHistory(
        instructor_id=instructor_id,
        student_id=student_id,
        assignment_id=assignment_id,
        status=status,
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


async def messages_for_history(db: AsyncSession, history_id: int) -> list[AssignmentHistoryMessage]:
    result = await db.execute(
        select(AssignmentHistoryMessage)
        .where(AssignmentHistoryMessage.assignment_history_id == history_id)
        .options(selectinload(AssignmentHistoryMessage.sender))
        .order_by(AssignmentHistoryMessage.created_at.desc())
    )
    return list(result.scalars().all())


async def count_sender_messages(db: AsyncSession, *, history_id: int, sender_id: int) -> int:
    result = await db.execute(
        select(func.count(AssignmentHistoryMessage.id)).where(
            AssignmentHistoryMessage.assignment_history_id == history_id,
            AssignmentHistoryMessage.sender_id == sender_id,
        )
    )
    return result.scalar_one()


async def create_message(
    db: AsyncSession,
    *,
    history_id: int,
    sender_id: int,
    message: str,
    file_title: str | None,
    file_path: str | None,
) -> AssignmentHistoryMessage:
    msg = AssignmentHistoryMessage(
        assignment_history_id=history_id,
        sender_id=sender_id,
        message=message,
        file_title=file_title,
        file_path=file_path,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg, attribute_names=["sender"])
    return msg
