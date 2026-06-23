from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, CourseStatus, CourseType


def _catalogue():
    """Base catalogue query: active, non-private, teacher/category eager-loaded."""
    return (
        select(Course)
        .where(Course.status == CourseStatus.active, Course.private.is_(False))
        .options(selectinload(Course.teacher), selectinload(Course.category))
    )


async def list_courses(
    db: AsyncSession,
    *,
    category: int | None = None,
    free: bool | None = None,
    course_type: CourseType | None = None,
    upcoming: bool | None = None,
    downloadable: bool | None = None,
    reward: bool | None = None,
    sort: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Course]:
    """Legacy WebinarController@index + scopeHandleFilters (column-backed filters).

    Filters depending on unported subsystems (discount/filter_option/moreOptions)
    are deferred to their phases.
    """
    stmt = _catalogue()
    if category is not None:
        stmt = stmt.where(Course.category_id == category)
    if free:
        stmt = stmt.where(Course.price == 0)
    if course_type is not None:
        stmt = stmt.where(Course.type == course_type)
    if upcoming:
        stmt = stmt.where(Course.start_date.is_not(None), Course.start_date >= datetime.now(UTC))
    if downloadable:
        stmt = stmt.where(Course.downloadable.is_(True))
    if reward:
        stmt = stmt.where(Course.points.is_not(None))

    order = {
        "expensive": Course.price.desc(),
        "cheapest": Course.price.asc(),
        "oldest": Course.created_at.asc(),
    }.get(sort or "", Course.created_at.desc())

    result = await db.execute(stmt.order_by(order).limit(limit).offset(offset))
    return list(result.scalars().all())


async def search_by_title(db: AsyncSession, query: str, limit: int = 50) -> list[Course]:
    """Legacy SearchController: active, non-private, title LIKE %query%."""
    result = await db.execute(_catalogue().where(Course.title.ilike(f"%{query}%")).limit(limit))
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
