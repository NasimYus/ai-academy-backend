from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bundle import Bundle, BundleWebinar
from app.models.course import Course


async def list_for_instructor(db: AsyncSession, user_id: int) -> list[Bundle]:
    """Bundles the instructor owns (creator or teacher), newest-updated first."""
    result = await db.execute(
        select(Bundle)
        .where(or_(Bundle.creator_id == user_id, Bundle.teacher_id == user_id))
        .options(selectinload(Bundle.category), selectinload(Bundle.webinars))
        .order_by(Bundle.updated_at.desc())
    )
    return list(result.scalars().all())


async def total_hours(db: AsyncSession, bundle_ids: list[int]) -> int:
    """Sum of the durations of the courses across the given bundles."""
    if not bundle_ids:
        return 0
    result = await db.execute(
        select(func.coalesce(func.sum(Course.duration), 0))
        .select_from(BundleWebinar)
        .join(Course, Course.id == BundleWebinar.course_id)
        .where(BundleWebinar.bundle_id.in_(bundle_ids))
    )
    return int(result.scalar_one() or 0)


async def get_owned(db: AsyncSession, bundle_id: int, user_id: int) -> Bundle | None:
    result = await db.execute(
        select(Bundle).where(
            Bundle.id == bundle_id,
            or_(Bundle.creator_id == user_id, Bundle.teacher_id == user_id),
        )
    )
    return result.scalar_one_or_none()


async def delete(db: AsyncSession, bundle: Bundle) -> None:
    await db.delete(bundle)
    await db.commit()
