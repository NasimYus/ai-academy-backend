from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gift import Gift, GiftStatus


async def create(db: AsyncSession, gift: Gift) -> Gift:
    db.add(gift)
    await db.flush()
    return gift


async def get_by_id(db: AsyncSession, gift_id: int) -> Gift | None:
    return await db.get(Gift, gift_id)


async def received_for_email(db: AsyncSession, email: str) -> list[Gift]:
    """Active gifts addressed to this email (the recipient inbox), newest first."""
    result = await db.execute(
        select(Gift)
        .where(Gift.email == email, Gift.status == GiftStatus.active)
        .order_by(Gift.created_at.desc(), Gift.id.desc())
    )
    return list(result.scalars().all())


async def sent_by_user(db: AsyncSession, user_id: int) -> list[Gift]:
    result = await db.execute(
        select(Gift).where(Gift.user_id == user_id).order_by(Gift.created_at.desc(), Gift.id.desc())
    )
    return list(result.scalars().all())
