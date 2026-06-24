from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow import Follow
from app.models.user import User


async def get(db: AsyncSession, *, follower_id: int, user_id: int) -> Follow | None:
    result = await db.execute(
        select(Follow).where(Follow.follower_id == follower_id, Follow.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def add(db: AsyncSession, *, follower_id: int, user_id: int) -> None:
    db.add(Follow(follower_id=follower_id, user_id=user_id))
    await db.commit()


async def remove(db: AsyncSession, follow: Follow) -> None:
    await db.delete(follow)
    await db.commit()


async def followers_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count()).select_from(Follow).where(Follow.user_id == user_id)
    )
    return int(result.scalar_one())


async def following(db: AsyncSession, follower_id: int) -> list[User]:
    """Users the given user follows (newest first)."""
    result = await db.execute(
        select(User)
        .join(Follow, Follow.user_id == User.id)
        .where(Follow.follower_id == follower_id)
        .order_by(Follow.id.desc())
    )
    return list(result.scalars().all())
