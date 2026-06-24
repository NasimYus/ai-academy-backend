from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course
from app.models.support import Support, SupportConversation, SupportDepartment, SupportStatus

# Eager-load everything `details` needs (relationships are lazy="raise").
_DETAIL_LOADS = (
    selectinload(Support.user),
    selectinload(Support.course),
    selectinload(Support.department),
    selectinload(Support.conversations).selectinload(SupportConversation.sender),
    selectinload(Support.conversations).selectinload(SupportConversation.supporter),
)


async def taught_course_ids(db: AsyncSession, teacher_id: int) -> list[int]:
    """Ids of courses the user teaches (legacy `$user->webinars`)."""
    result = await db.execute(select(Course.id).where(Course.teacher_id == teacher_id))
    return list(result.scalars().all())


def _ordered(query):
    return query.order_by(Support.created_at.desc(), Support.status.asc())


async def class_support(db: AsyncSession, user_id: int) -> list[Support]:
    """Course tickets the user opened (department_id null, user_id = me)."""
    result = await db.execute(
        _ordered(
            select(Support)
            .where(Support.department_id.is_(None), Support.user_id == user_id)
            .options(*_DETAIL_LOADS)
        )
    )
    return list(result.scalars().all())


async def my_class_support(db: AsyncSession, course_ids: list[int]) -> list[Support]:
    """Course tickets on courses the user teaches (department_id null)."""
    if not course_ids:
        return []
    result = await db.execute(
        _ordered(
            select(Support)
            .where(Support.department_id.is_(None), Support.course_id.in_(course_ids))
            .options(*_DETAIL_LOADS)
        )
    )
    return list(result.scalars().all())


async def platform_support(db: AsyncSession, user_id: int) -> list[Support]:
    """Platform tickets the user opened (department_id not null, user_id = me)."""
    result = await db.execute(
        _ordered(
            select(Support)
            .where(Support.department_id.is_not(None), Support.user_id == user_id)
            .options(*_DETAIL_LOADS)
        )
    )
    return list(result.scalars().all())


async def get_detail(db: AsyncSession, support_id: int) -> Support | None:
    result = await db.execute(
        select(Support).where(Support.id == support_id).options(*_DETAIL_LOADS)
    )
    return result.scalar_one_or_none()


async def get_for_participant(
    db: AsyncSession, support_id: int, *, user_id: int, course_ids: list[int]
) -> Support | None:
    """A ticket the user can act on: they opened it, or it targets their course."""
    clause = Support.user_id == user_id
    if course_ids:
        clause = or_(clause, Support.course_id.in_(course_ids))
    result = await db.execute(
        select(Support).where(Support.id == support_id, clause).options(*_DETAIL_LOADS)
    )
    return result.scalar_one_or_none()


async def create_support(
    db: AsyncSession,
    *,
    user_id: int,
    title: str,
    course_id: int | None,
    department_id: int | None,
    message: str,
    attach: str | None,
) -> Support:
    support = Support(
        user_id=user_id,
        title=title,
        course_id=course_id,
        department_id=department_id,
        status=SupportStatus.open,
    )
    db.add(support)
    await db.flush()
    db.add(
        SupportConversation(
            support_id=support.id, sender_id=user_id, message=message, attach=attach
        )
    )
    await db.commit()
    return support


async def add_conversation(
    db: AsyncSession,
    *,
    support: Support,
    sender_id: int,
    message: str,
    attach: str | None,
    status: SupportStatus,
) -> SupportConversation:
    support.status = status
    conversation = SupportConversation(
        support_id=support.id, sender_id=sender_id, message=message, attach=attach
    )
    db.add(conversation)
    await db.commit()
    return conversation


async def set_status(db: AsyncSession, support: Support, status: SupportStatus) -> None:
    support.status = status
    await db.commit()


async def list_departments(db: AsyncSession) -> list[SupportDepartment]:
    result = await db.execute(select(SupportDepartment).order_by(SupportDepartment.id.asc()))
    return list(result.scalars().all())


async def department_exists(db: AsyncSession, department_id: int) -> bool:
    result = await db.execute(
        select(SupportDepartment.id).where(SupportDepartment.id == department_id)
    )
    return result.scalar_one_or_none() is not None
