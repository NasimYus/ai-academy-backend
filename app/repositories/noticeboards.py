from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.noticeboard import CourseNoticeboard


async def list_for_course(db: AsyncSession, course_id: int) -> list[CourseNoticeboard]:
    """Course announcements, newest first (legacy `$webinar->noticeboards`)."""
    result = await db.execute(
        select(CourseNoticeboard)
        .where(CourseNoticeboard.course_id == course_id)
        .options(selectinload(CourseNoticeboard.creator))
        .order_by(CourseNoticeboard.id.desc())
    )
    return list(result.scalars().all())
