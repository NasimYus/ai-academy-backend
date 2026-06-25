from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, ProductCategory, ProductStatus


async def list_active(db: AsyncSession, category_id: int | None = None) -> list[Product]:
    """Active, orderable products for the public store (legacy index)."""
    stmt = (
        select(Product)
        .where(Product.status == ProductStatus.active, Product.ordering.is_(True))
        .options(selectinload(Product.category))
        .order_by(Product.created_at.desc())
    )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_active(db: AsyncSession, product_id: int) -> Product | None:
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.status == ProductStatus.active)
        .options(selectinload(Product.category))
    )
    return result.scalar_one_or_none()


async def list_by_creator(db: AsyncSession, user_id: int) -> list[Product]:
    """The instructor's own products (legacy store/products)."""
    result = await db.execute(
        select(Product)
        .where(Product.creator_id == user_id)
        .options(selectinload(Product.category))
        .order_by(Product.created_at.desc())
    )
    return list(result.scalars().all())


async def list_categories(db: AsyncSession) -> list[ProductCategory]:
    result = await db.execute(select(ProductCategory).order_by(ProductCategory.order.asc()))
    return list(result.scalars().all())


def group_categories(categories: list[ProductCategory]) -> tuple[list[ProductCategory], dict]:
    """Split into top-level + children-by-parent."""
    tops = [c for c in categories if c.parent_id is None]
    children: dict[int, list[ProductCategory]] = defaultdict(list)
    for c in categories:
        if c.parent_id is not None:
            children[c.parent_id].append(c)
    return tops, children
