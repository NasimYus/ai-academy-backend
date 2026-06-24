from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course
from app.models.favorite import Favorite


async def list_for_user(db: AsyncSession, user_id: int) -> list[Favorite]:
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .options(
            selectinload(Favorite.course).selectinload(Course.teacher),
            selectinload(Favorite.course).selectinload(Course.category),
            selectinload(Favorite.course).selectinload(Course.translations),
        )
        .order_by(Favorite.id.desc())
    )
    return list(result.scalars().all())


async def get(db: AsyncSession, *, user_id: int, course_id: int) -> Favorite | None:
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.course_id == course_id)
    )
    return result.scalar_one_or_none()


async def get_owned(db: AsyncSession, favorite_id: int, user_id: int) -> Favorite | None:
    result = await db.execute(
        select(Favorite).where(Favorite.id == favorite_id, Favorite.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def add(db: AsyncSession, *, user_id: int, course_id: int) -> None:
    db.add(Favorite(user_id=user_id, course_id=course_id))
    await db.commit()


async def remove(db: AsyncSession, favorite: Favorite) -> None:
    await db.delete(favorite)
    await db.commit()
