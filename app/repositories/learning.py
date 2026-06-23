from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning import CourseLearning

# Maps the API item type to the CourseLearning column.
COLUMN_BY_TYPE = {
    "file": "file_id",
    "text_lesson": "text_lesson_id",
    "session": "session_id",
}


async def toggle(
    db: AsyncSession, *, user_id: int, course_id: int, item_type: str, item_id: int, learned: bool
) -> None:
    column = COLUMN_BY_TYPE[item_type]
    await db.execute(
        delete(CourseLearning).where(
            CourseLearning.user_id == user_id,
            getattr(CourseLearning, column) == item_id,
        )
    )
    if learned:
        row = CourseLearning(user_id=user_id, course_id=course_id)
        setattr(row, column, item_id)
        db.add(row)
    await db.commit()


async def learned_keys(db: AsyncSession, user_id: int, course_id: int) -> set[tuple[str, int]]:
    """Set of (item_type, item_id) the user has marked learned in the course."""
    result = await db.execute(
        select(CourseLearning).where(
            CourseLearning.user_id == user_id, CourseLearning.course_id == course_id
        )
    )
    keys: set[tuple[str, int]] = set()
    for row in result.scalars().all():
        if row.file_id is not None:
            keys.add(("file", row.file_id))
        if row.text_lesson_id is not None:
            keys.add(("text_lesson", row.text_lesson_id))
        if row.session_id is not None:
            keys.add(("session", row.session_id))
    return keys
