from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product_order import ProductOrder


async def list_for_buyer(db: AsyncSession, buyer_id: int) -> list[ProductOrder]:
    result = await db.execute(
        select(ProductOrder)
        .where(ProductOrder.buyer_id == buyer_id)
        .options(selectinload(ProductOrder.product))
        .order_by(ProductOrder.created_at.desc(), ProductOrder.id.desc())
    )
    return list(result.scalars().all())
