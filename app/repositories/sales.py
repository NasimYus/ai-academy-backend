from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sale import Sale


async def seller_sales(db: AsyncSession, seller_id: int) -> list[Sale]:
    result = await db.execute(
        select(Sale)
        .where(Sale.seller_id == seller_id, Sale.refund_at.is_(None))
        .order_by(Sale.created_at.desc(), Sale.id.desc())
    )
    return list(result.scalars().all())


async def seller_income(db: AsyncSession, seller_id: int) -> float:
    result = await db.execute(
        select(func.coalesce(func.sum(Sale.total_amount), 0)).where(
            Sale.seller_id == seller_id, Sale.refund_at.is_(None)
        )
    )
    return float(result.scalar_one())


async def buyer_sales(db: AsyncSession, buyer_id: int) -> list[Sale]:
    result = await db.execute(
        select(Sale)
        .where(Sale.buyer_id == buyer_id)
        .order_by(Sale.created_at.desc(), Sale.id.desc())
    )
    return list(result.scalars().all())
