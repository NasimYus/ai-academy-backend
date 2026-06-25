from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.models.course import Course


async def list_for_course(db: AsyncSession, course_id: int) -> list[Comment]:
    """All comments for a course (newest first), reviewer eager-loaded."""
    result = await db.execute(
        select(Comment)
        .where(Comment.course_id == course_id)
        .options(selectinload(Comment.user))
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())


# --- instructor "my class comments" (Phase 6.4) ---


def _taught_courses(user_id: int):
    return select(Course.id).where(or_(Course.creator_id == user_id, Course.teacher_id == user_id))


async def list_for_instructor(db: AsyncSession, user_id: int) -> list[Comment]:
    """Comments on courses the instructor teaches (newest first), author loaded."""
    result = await db.execute(
        select(Comment)
        .where(Comment.course_id.in_(_taught_courses(user_id)))
        .options(selectinload(Comment.user))
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())


async def get_for_instructor(db: AsyncSession, comment_id: int, user_id: int) -> Comment | None:
    """A comment on one of the instructor's courses (reply is scoped to these)."""
    result = await db.execute(
        select(Comment).where(
            Comment.id == comment_id, Comment.course_id.in_(_taught_courses(user_id))
        )
    )
    return result.scalar_one_or_none()


async def create_reply(db: AsyncSession, *, parent: Comment, user_id: int, text: str) -> Comment:
    reply = Comment(
        course_id=parent.course_id,
        blog_id=parent.blog_id,
        user_id=user_id,
        reply_id=parent.id,
        comment=text,
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return reply
