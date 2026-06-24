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
