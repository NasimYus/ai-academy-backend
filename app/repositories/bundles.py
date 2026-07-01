from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bundle import Bundle, BundleStatus, BundleWebinar
from app.models.course import Course, CourseStatus


async def list_active(db: AsyncSession) -> list[Bundle]:
    """Active bundles for the public catalogue (legacy Web\\BundleController@index)."""
    result = await db.execute(
        select(Bundle)
        .where(Bundle.status == BundleStatus.active)
        .options(selectinload(Bundle.category), selectinload(Bundle.webinars))
        .order_by(Bundle.created_at.desc())
    )
    return list(result.scalars().all())


async def get_active(db: AsyncSession, bundle_id: int) -> Bundle | None:
    """An active bundle with its active courses eager-loaded."""
    result = await db.execute(
        select(Bundle)
        .where(Bundle.id == bundle_id, Bundle.status == BundleStatus.active)
        .options(
            selectinload(Bundle.category),
            selectinload(Bundle.webinars)
            .selectinload(BundleWebinar.course)
            .selectinload(Course.teacher),
            selectinload(Bundle.webinars)
            .selectinload(BundleWebinar.course)
            .selectinload(Course.category),
        )
    )
    return result.scalar_one_or_none()


async def active_course_ids(db: AsyncSession, bundle_id: int) -> list[int]:
    """Ids of active courses in a bundle (the access grant target)."""
    result = await db.execute(
        select(BundleWebinar.course_id)
        .join(Course, Course.id == BundleWebinar.course_id)
        .where(BundleWebinar.bundle_id == bundle_id, Course.status == CourseStatus.active)
    )
    return [row[0] for row in result.all()]


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


def _slugify(title: str) -> str:
    import re

    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return base or "bundle"


async def unique_slug(db: AsyncSession, title: str) -> str:
    base = _slugify(title)
    slug = base
    i = 1
    while await db.scalar(select(Bundle.id).where(Bundle.slug == slug)) is not None:
        i += 1
        slug = f"{base}-{i}"
    return slug


async def create(db: AsyncSession, bundle: Bundle) -> Bundle:
    db.add(bundle)
    await db.commit()
    await db.refresh(bundle)
    return bundle


async def list_all(db: AsyncSession) -> list[Bundle]:
    """All bundles for the admin list (legacy Admin\\BundleController@index)."""
    result = await db.execute(
        select(Bundle)
        .options(selectinload(Bundle.category), selectinload(Bundle.webinars))
        .order_by(Bundle.created_at.desc())
    )
    return list(result.scalars().all())


async def webinar_counts(db: AsyncSession, bundle_ids: list[int]) -> dict[int, int]:
    if not bundle_ids:
        return {}
    rows = await db.execute(
        select(BundleWebinar.bundle_id, func.count())
        .where(BundleWebinar.bundle_id.in_(bundle_ids))
        .group_by(BundleWebinar.bundle_id)
    )
    return {bid: int(c) for bid, c in rows.all()}
