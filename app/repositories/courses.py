from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, CourseStatus


async def list_published(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[Course]:
    result = await db.execute(
        select(Course)
        .where(Course.status == CourseStatus.published)
        .order_by(Course.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_by_slug(db: AsyncSession, slug: str) -> Course | None:
    result = await db.execute(select(Course).where(Course.slug == slug))
    return result.scalar_one_or_none()
