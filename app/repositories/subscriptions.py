from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.subscription import Subscribe, SubscribeUse, UserSubscribe


async def list_plans(db: AsyncSession) -> list[Subscribe]:
    result = await db.execute(select(Subscribe).order_by(Subscribe.price.asc()))
    return list(result.scalars().all())


async def get_plan(db: AsyncSession, plan_id: int) -> Subscribe | None:
    return await db.get(Subscribe, plan_id)


async def latest_user_subscribe(db: AsyncSession, user_id: int) -> UserSubscribe | None:
    """The user's most recent activated subscription (legacy latest subscribe Sale)."""
    result = await db.execute(
        select(UserSubscribe)
        .where(UserSubscribe.user_id == user_id)
        .options(selectinload(UserSubscribe.subscribe))
        .order_by(UserSubscribe.created_at.desc())
    )
    return result.scalars().first()


async def count_uses(db: AsyncSession, user_id: int, subscribe_id: int) -> int:
    result = await db.execute(
        select(func.count(SubscribeUse.id)).where(
            SubscribeUse.user_id == user_id, SubscribeUse.subscribe_id == subscribe_id
        )
    )
    return int(result.scalar_one())


async def create_user_subscribe(
    db: AsyncSession, *, user_id: int, subscribe_id: int
) -> UserSubscribe:
    row = UserSubscribe(user_id=user_id, subscribe_id=subscribe_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def create_use(
    db: AsyncSession, *, user_id: int, subscribe_id: int, course_id: int
) -> SubscribeUse:
    row = SubscribeUse(user_id=user_id, subscribe_id=subscribe_id, course_id=course_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
