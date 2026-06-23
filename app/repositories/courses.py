from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, CourseStatus


async def list_published(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[Course]:
    """Legacy WebinarController@index: active, non-private, newest first.

    Eager-loads teacher/category so serialization never triggers a lazy load
    outside the session (relationships are `lazy="raise"`).
    """
    result = await db.execute(
        select(Course)
        .where(Course.status == CourseStatus.active, Course.private.is_(False))
        .options(selectinload(Course.teacher), selectinload(Course.category))
        .order_by(Course.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_by_slug(db: AsyncSession, slug: str) -> Course | None:
    """Legacy WebinarController@show: non-private match by slug."""
    result = await db.execute(
        select(Course)
        .where(Course.slug == slug, Course.private.is_(False))
        .options(selectinload(Course.teacher), selectinload(Course.category))
    )
    return result.scalar_one_or_none()


async def counts_by_category(db: AsyncSession) -> dict[int, int]:
    """webinars_count per category_id (legacy: all courses, no status filter)."""
    result = await db.execute(
        select(Course.category_id, func.count(Course.id))
        .where(Course.category_id.is_not(None))
        .group_by(Course.category_id)
    )
    return {category_id: count for category_id, count in result.all()}
