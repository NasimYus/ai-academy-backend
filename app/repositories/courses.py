import re
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Chapter
from app.models.course import Course, CourseStatus, CourseType


def _catalogue():
    """Base catalogue query: active, non-private, teacher/category eager-loaded."""
    return (
        select(Course)
        .where(Course.status == CourseStatus.active, Course.private.is_(False))
        .options(
            selectinload(Course.teacher),
            selectinload(Course.category),
            selectinload(Course.translations),
        )
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


async def with_reward_points(db: AsyncSession) -> list[Course]:
    """Active, non-private courses buyable with points (legacy RewardsController@courses)."""
    result = await db.execute(_catalogue().where(Course.points.is_not(None)))
    return list(result.scalars().all())


async def search_by_title(db: AsyncSession, query: str, limit: int = 50) -> list[Course]:
    """Legacy SearchController: active, non-private, title LIKE %query%."""
    result = await db.execute(_catalogue().where(Course.title.ilike(f"%{query}%")).limit(limit))
    return list(result.scalars().all())


async def list_by_teacher(db: AsyncSession, teacher_id: int) -> list[Course]:
    """Active, non-private courses taught by a user (for public profiles)."""
    result = await db.execute(
        _catalogue().where(Course.teacher_id == teacher_id).order_by(Course.created_at.desc())
    )
    return list(result.scalars().all())


async def list_featured(db: AsyncSession) -> list[Course]:
    """Legacy FeatureWebinarController@index: home/home_categories, published.

    Returns the related active, non-private courses (newest-featured first).
    """
    from app.models.featured_course import FeaturedCourse, FeaturedPage, FeaturedStatus

    result = await db.execute(
        select(FeaturedCourse)
        .join(Course, FeaturedCourse.course_id == Course.id)
        .where(
            FeaturedCourse.page.in_([FeaturedPage.home, FeaturedPage.home_categories]),
            FeaturedCourse.status == FeaturedStatus.publish,
            Course.status == CourseStatus.active,
            Course.private.is_(False),
        )
        .options(
            selectinload(FeaturedCourse.course).selectinload(Course.teacher),
            selectinload(FeaturedCourse.course).selectinload(Course.category),
        )
        .order_by(FeaturedCourse.order.asc(), FeaturedCourse.updated_at.desc())
    )
    return [fc.course for fc in result.scalars().all()]


async def get_by_id(db: AsyncSession, course_id: int) -> Course | None:
    return await db.get(Course, course_id)


async def get_by_slug(db: AsyncSession, slug: str) -> Course | None:
    """Legacy WebinarController@show: non-private match by slug."""
    result = await db.execute(
        select(Course)
        .where(Course.slug == slug, Course.private.is_(False))
        .options(
            selectinload(Course.teacher),
            selectinload(Course.category),
            selectinload(Course.translations),
        )
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


# --- instructor mutations (Phase 6.1) ---


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "course"


async def unique_slug(db: AsyncSession, title: str) -> str:
    """A URL slug from the title, made unique with a numeric suffix."""
    base = _slugify(title)
    candidate = base
    i = 2
    while (await db.execute(select(Course.id).where(Course.slug == candidate))).first():
        candidate = f"{base}-{i}"
        i += 1
    return candidate


async def create_course(db: AsyncSession, course: Course) -> Course:
    db.add(course)
    await db.commit()
    await db.refresh(course, attribute_names=["teacher", "category"])
    return course


async def update_course(db: AsyncSession, course: Course, changes: dict) -> Course:
    for key, value in changes.items():
        setattr(course, key, value)
    await db.commit()
    await db.refresh(course, attribute_names=["teacher", "category"])
    return course


async def delete_course(db: AsyncSession, course: Course) -> None:
    await db.delete(course)
    await db.commit()


async def list_by_creator(db: AsyncSession, user_id: int) -> list[Course]:
    """Courses the user owns as creator or teacher (legacy classes list)."""
    result = await db.execute(
        select(Course)
        .where((Course.creator_id == user_id) | (Course.teacher_id == user_id))
        .options(selectinload(Course.teacher), selectinload(Course.category))
        .order_by(Course.created_at.desc())
    )
    return list(result.scalars().all())


async def get_owned(db: AsyncSession, course_id: int, user_id: int) -> Course | None:
    result = await db.execute(
        select(Course)
        .where(
            Course.id == course_id,
            (Course.creator_id == user_id) | (Course.teacher_id == user_id),
        )
        .options(selectinload(Course.teacher), selectinload(Course.category))
    )
    return result.scalar_one_or_none()


async def get_chapter(db: AsyncSession, chapter_id: int) -> Chapter | None:
    return await db.get(Chapter, chapter_id)
