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


_MODEL_BY_TYPE = {"file": File, "text_lesson": TextLesson, "session": CourseSession}


async def item_belongs_to_course(
    db: AsyncSession, item_type: str, item_id: int, course_id: int
) -> bool:
    model = _MODEL_BY_TYPE.get(item_type)
    if model is None:
        return False
    result = await db.execute(
        select(model.id).where(model.id == item_id, model.course_id == course_id)
    )
    return result.first() is not None


async def sessions_for_course(db: AsyncSession, course_id: int) -> list[CourseSession]:
    result = await db.execute(
        select(CourseSession)
        .where(CourseSession.course_id == course_id)
        .order_by(CourseSession.order.asc())
    )
    return list(result.scalars().all())
