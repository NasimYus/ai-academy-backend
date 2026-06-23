from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment


async def list_for_course(db: AsyncSession, course_id: int) -> list[Comment]:
    """All comments for a course (newest first), reviewer eager-loaded."""
    result = await db.execute(
        select(Comment)
        .where(Comment.course_id == course_id)
        .options(selectinload(Comment.user))
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())
