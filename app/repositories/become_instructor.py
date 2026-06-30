from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.become_instructor import BecomeInstructor, BecomeInstructorStatus


async def get_for_user(db: AsyncSession, user_id: int) -> BecomeInstructor | None:
    result = await db.execute(
        select(BecomeInstructor).where(BecomeInstructor.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, request_id: int) -> BecomeInstructor | None:
    result = await db.execute(
        select(BecomeInstructor)
        .where(BecomeInstructor.id == request_id)
        .options(selectinload(BecomeInstructor.user))
    )
    return result.scalar_one_or_none()


async def upsert(
    db: AsyncSession,
    *,
    user_id: int,
    role: str,
    description: str | None,
    occupations: list[int] | None,
) -> BecomeInstructor:
    """Legacy updateOrCreate on user_id — re-submitting overwrites the request."""
    existing = await get_for_user(db, user_id)
    if existing is None:
        existing = BecomeInstructor(user_id=user_id)
        db.add(existing)
    existing.role = role
    existing.description = description
    existing.occupations = occupations
    existing.status = BecomeInstructorStatus.pending
    await db.commit()
    await db.refresh(existing)
    return existing


async def list_requests(
    db: AsyncSession, *, status: BecomeInstructorStatus | None = None
) -> list[BecomeInstructor]:
    stmt = select(BecomeInstructor).options(selectinload(BecomeInstructor.user))
    if status is not None:
        stmt = stmt.where(BecomeInstructor.status == status)
    result = await db.execute(stmt.order_by(BecomeInstructor.created_at.desc()))
    return list(result.scalars().all())


async def set_status(
    db: AsyncSession, request: BecomeInstructor, status: BecomeInstructorStatus
) -> BecomeInstructor:
    request.status = status
    await db.commit()
    await db.refresh(request)
    return request
