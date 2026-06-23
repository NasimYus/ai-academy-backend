from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Chapter, ChapterStatus, CourseSession, File, TextLesson


async def chapters_for_course(db: AsyncSession, course_id: int) -> list[Chapter]:
    result = await db.execute(
        select(Chapter)
        .where(Chapter.course_id == course_id, Chapter.status == ChapterStatus.active)
        .order_by(Chapter.order.asc())
    )
    return list(result.scalars().all())


async def files_for_course(db: AsyncSession, course_id: int) -> list[File]:
    result = await db.execute(
        select(File).where(File.course_id == course_id).order_by(File.order.asc())
    )
    return list(result.scalars().all())


async def text_lessons_for_course(db: AsyncSession, course_id: int) -> list[TextLesson]:
    result = await db.execute(
        select(TextLesson).where(TextLesson.course_id == course_id).order_by(TextLesson.order.asc())
    )
    return list(result.scalars().all())


async def sessions_for_course(db: AsyncSession, course_id: int) -> list[CourseSession]:
    result = await db.execute(
        select(CourseSession)
        .where(CourseSession.course_id == course_id)
        .order_by(CourseSession.order.asc())
    )
    return list(result.scalars().all())
