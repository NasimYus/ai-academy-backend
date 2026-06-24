from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import CartItem
from app.models.course import Course


async def list_for_user(db: AsyncSession, user_id: int) -> list[CartItem]:
    result = await db.execute(
        select(CartItem)
        .where(CartItem.creator_id == user_id)
        .options(selectinload(CartItem.course).selectinload(Course.teacher))
        .order_by(CartItem.id.desc())
    )
    return list(result.scalars().all())


async def exists(db: AsyncSession, *, user_id: int, course_id: int) -> bool:
    result = await db.execute(
        select(CartItem.id).where(CartItem.creator_id == user_id, CartItem.course_id == course_id)
    )
    return result.first() is not None


async def add(db: AsyncSession, *, user_id: int, course_id: int) -> CartItem:
    row = CartItem(creator_id=user_id, course_id=course_id)
    db.add(row)
    await db.commit()
    result = await db.execute(
        select(CartItem)
        .where(CartItem.id == row.id)
        .options(selectinload(CartItem.course).selectinload(Course.teacher))
    )
    return result.scalar_one()


async def get_owned(db: AsyncSession, item_id: int, user_id: int) -> CartItem | None:
    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.creator_id == user_id)
    )
    return result.scalar_one_or_none()


async def remove(db: AsyncSession, item: CartItem) -> None:
    await db.delete(item)
    await db.commit()
