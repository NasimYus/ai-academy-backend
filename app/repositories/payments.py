from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import PaymentChannel, PaymentChannelStatus


async def list_active(db: AsyncSession) -> list[PaymentChannel]:
    result = await db.execute(
        select(PaymentChannel)
        .where(PaymentChannel.status == PaymentChannelStatus.active)
        .order_by(PaymentChannel.id.asc())
    )
    return list(result.scalars().all())


async def get_active(db: AsyncSession, channel_id: int) -> PaymentChannel | None:
    result = await db.execute(
        select(PaymentChannel).where(
            PaymentChannel.id == channel_id,
            PaymentChannel.status == PaymentChannelStatus.active,
        )
    )
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession) -> list[PaymentChannel]:
    """All channels regardless of status, newest first (admin)."""
    result = await db.execute(
        select(PaymentChannel).order_by(PaymentChannel.created_at.desc(), PaymentChannel.id.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, channel_id: int) -> PaymentChannel | None:
    return await db.get(PaymentChannel, channel_id)


async def get_active_by_class(db: AsyncSession, class_name: str) -> PaymentChannel | None:
    result = await db.execute(
        select(PaymentChannel)
        .where(
            PaymentChannel.class_name == class_name,
            PaymentChannel.status == PaymentChannelStatus.active,
        )
        .order_by(PaymentChannel.id.asc())
    )
    return result.scalars().first()
