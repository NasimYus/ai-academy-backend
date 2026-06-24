from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blog import Blog, BlogCategory, BlogStatus
from app.models.comment import Comment

_LOADS = (selectinload(Blog.author), selectinload(Blog.category))


async def list_published(
    db: AsyncSession,
    *,
    category_id: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[Blog]:
    """Published posts, newest-updated first (legacy BlogController@index)."""
    query = select(Blog).where(Blog.status == BlogStatus.publish).options(*_LOADS)
    if category_id is not None:
        query = query.where(Blog.category_id == category_id)
    query = query.order_by(Blog.updated_at.desc(), Blog.created_at.desc())
    # Legacy applies offset only when both offset and limit are present.
    if limit is not None:
        if offset:
            query = query.offset(offset)
        query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_published(db: AsyncSession, blog_id: int) -> Blog | None:
    result = await db.execute(
        select(Blog).where(Blog.id == blog_id, Blog.status == BlogStatus.publish).options(*_LOADS)
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, blog_id: int) -> Blog | None:
    result = await db.execute(select(Blog).where(Blog.id == blog_id))
    return result.scalar_one_or_none()


async def comment_counts(db: AsyncSession, blog_ids: list[int]) -> dict[int, int]:
    """Comment count per blog id (single grouped query)."""
    if not blog_ids:
        return {}
    result = await db.execute(
        select(Comment.blog_id, func.count())
        .where(Comment.blog_id.in_(blog_ids))
        .group_by(Comment.blog_id)
    )
    return {bid: n for bid, n in result.all()}


async def list_comments(db: AsyncSession, blog_id: int) -> list[Comment]:
    """All comments for a blog (oldest first), author eager-loaded."""
    result = await db.execute(
        select(Comment)
        .where(Comment.blog_id == blog_id)
        .options(selectinload(Comment.user))
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())


async def add_comment(
    db: AsyncSession, *, blog_id: int, user_id: int, comment: str, reply_id: int | None
) -> Comment:
    row = Comment(blog_id=blog_id, user_id=user_id, comment=comment, reply_id=reply_id)
    db.add(row)
    await db.commit()
    return row


async def list_categories(db: AsyncSession) -> list[BlogCategory]:
    result = await db.execute(select(BlogCategory).order_by(BlogCategory.id.asc()))
    return list(result.scalars().all())
