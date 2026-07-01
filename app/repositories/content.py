from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Chapter, ChapterStatus, CourseSession, File, TextLesson


async def chapters_for_course(db: AsyncSession, course_id: int) -> list[Chapter]:
    result = await db.execute(
        select(Chapter)
        .where(Chapter.course_id == course_id, Chapter.status == ChapterStatus.active)
        .order_by(Chapter.order.asc())
    )
    return list(result.scalars().all())


async def get_chapter(db: AsyncSession, chapter_id: int) -> Chapter | None:
    return await db.get(Chapter, chapter_id)


async def create_chapter(db: AsyncSession, course_id: int, title: str) -> Chapter:
    next_order = await db.scalar(
        select(func.coalesce(func.max(Chapter.order), -1) + 1).where(Chapter.course_id == course_id)
    )
    chapter = Chapter(course_id=course_id, title=title, order=next_order or 0)
    db.add(chapter)
    await db.commit()
    await db.refresh(chapter)
    return chapter


async def update_chapter(db: AsyncSession, chapter: Chapter, title: str) -> Chapter:
    chapter.title = title
    await db.commit()
    await db.refresh(chapter)
    return chapter


async def delete_chapter(db: AsyncSession, chapter: Chapter) -> None:
    await db.delete(chapter)
    await db.commit()


async def reorder_chapters(db: AsyncSession, course_id: int, ordered_ids: list[int]) -> None:
    chapters = await chapters_for_course(db, course_id)
    by_id = {c.id: c for c in chapters}
    for index, cid in enumerate(ordered_ids):
        chapter = by_id.get(cid)
        if chapter is not None:
            chapter.order = index
    await db.commit()


async def chapter_item_counts(db: AsyncSession, course_id: int) -> dict[int, tuple[int, int]]:
    """Per-chapter (items_count, total_duration_minutes) for the manage list."""
    counts: dict[int, tuple[int, int]] = {}
    for model in (File, TextLesson, CourseSession):
        rows = await db.execute(
            select(model.chapter_id, model.id).where(model.course_id == course_id)
        )
        for chapter_id, _ in rows.all():
            if chapter_id is None:
                continue
            items, duration = counts.get(chapter_id, (0, 0))
            counts[chapter_id] = (items + 1, duration)
    # duration from sessions
    sessions = await db.execute(
        select(CourseSession.chapter_id, CourseSession.duration).where(
            CourseSession.course_id == course_id
        )
    )
    for chapter_id, duration in sessions.all():
        if chapter_id is None:
            continue
        items, total = counts.get(chapter_id, (0, 0))
        counts[chapter_id] = (items, total + (duration or 0))
    return counts


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


ITEM_MODELS = {"session": CourseSession, "file": File, "text_lesson": TextLesson}

_ITEM_FIELDS = {
    "session": ("title", "session_date", "duration", "link", "description", "accessibility"),
    "file": ("title", "file", "volume", "file_type", "description", "accessibility"),
    "text_lesson": ("title", "image", "study_time", "summary", "content", "accessibility"),
}


async def create_item(
    db: AsyncSession, item_type: str, course_id: int, chapter_id: int, data: dict
):
    model = ITEM_MODELS[item_type]
    fields = {k: data[k] for k in _ITEM_FIELDS[item_type] if k in data}
    next_order = await db.scalar(
        select(func.coalesce(func.max(model.order), -1) + 1).where(model.chapter_id == chapter_id)
    )
    obj = model(course_id=course_id, chapter_id=chapter_id, order=next_order or 0, **fields)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_item(db: AsyncSession, item_type: str, item_id: int):
    model = ITEM_MODELS.get(item_type)
    if model is None:
        return None
    return await db.get(model, item_id)


async def update_item(db: AsyncSession, obj, item_type: str, data: dict):
    for key in _ITEM_FIELDS[item_type]:
        if key in data:
            setattr(obj, key, data[key])
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_item(db: AsyncSession, obj) -> None:
    await db.delete(obj)
    await db.commit()
