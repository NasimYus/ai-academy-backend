from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_note import CoursePersonalNote, NoteTargetType


async def find(
    db: AsyncSession, *, user_id: int, target_type: NoteTargetType, target_id: int
) -> CoursePersonalNote | None:
    result = await db.execute(
        select(CoursePersonalNote).where(
            CoursePersonalNote.user_id == user_id,
            CoursePersonalNote.target_type == target_type,
            CoursePersonalNote.target_id == target_id,
        )
    )
    return result.scalar_one_or_none()


async def upsert(
    db: AsyncSession,
    *,
    user_id: int,
    course_id: int,
    target_type: NoteTargetType,
    target_id: int,
    note: str | None,
) -> CoursePersonalNote:
    """Update-or-create on (user, course, target), parity of legacy updateOrCreate."""
    row = await find(db, user_id=user_id, target_type=target_type, target_id=target_id)
    if row is None:
        row = CoursePersonalNote(
            user_id=user_id, course_id=course_id, target_type=target_type, target_id=target_id
        )
        db.add(row)
    row.note = note
    await db.commit()
    await db.refresh(row)
    return row


async def get_owned(db: AsyncSession, note_id: int, user_id: int) -> CoursePersonalNote | None:
    result = await db.execute(
        select(CoursePersonalNote).where(
            CoursePersonalNote.id == note_id, CoursePersonalNote.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def set_attachment(db: AsyncSession, note: CoursePersonalNote, path: str) -> None:
    note.attachment = path
    await db.commit()
    await db.refresh(note)


async def delete(db: AsyncSession, note: CoursePersonalNote) -> None:
    await db.delete(note)
    await db.commit()
