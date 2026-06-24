from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.currency import Currency


async def list_all(db: AsyncSession) -> list[Currency]:
    result = await db.execute(
        select(Currency).order_by(Currency.order.asc().nullslast(), Currency.id.asc())
    )
    return list(result.scalars().all())


async def get_by_code(db: AsyncSession, code: str) -> Currency | None:
    result = await db.execute(select(Currency).where(Currency.currency == code))
    return result.scalar_one_or_none()
