from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem, OrderStatus


async def get_by_id(db: AsyncSession, order_id: int) -> Order | None:
    return await db.get(Order, order_id)


def _loaded():
    return selectinload(Order.items).selectinload(OrderItem.course)


async def list_for_user(db: AsyncSession, user_id: int) -> list[Order]:
    result = await db.execute(
        select(Order).where(Order.user_id == user_id).options(_loaded()).order_by(Order.id.desc())
    )
    return list(result.scalars().all())


async def get_owned(db: AsyncSession, order_id: int, user_id: int) -> Order | None:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user_id).options(_loaded())
    )
    return result.scalar_one_or_none()


async def reload(db: AsyncSession, order_id: int) -> Order:
    result = await db.execute(select(Order).where(Order.id == order_id).options(_loaded()))
    return result.scalar_one()


async def create(
    db: AsyncSession,
    *,
    user_id: int,
    amount: float,
    total_discount: float,
    total_amount: float,
    items: list[dict],
) -> Order:
    order = Order(
        user_id=user_id,
        status=OrderStatus.pending,
        amount=amount,
        tax=0,
        total_discount=total_discount,
        total_amount=total_amount,
    )
    db.add(order)
    await db.flush()
    for it in items:
        db.add(OrderItem(user_id=user_id, order_id=order.id, **it))
    await db.commit()
    return await reload(db, order.id)
