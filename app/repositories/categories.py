from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category, TrendCategory


async def list_top_level(db: AsyncSession) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.parent_id.is_(None), Category.enable.is_(True))
        .options(selectinload(Category.translations))
        .order_by(Category.order.asc())
    )
    return list(result.scalars().all())


async def children_by_parent(db: AsyncSession) -> dict[int, list[Category]]:
    result = await db.execute(
        select(Category)
        .where(Category.parent_id.is_not(None), Category.enable.is_(True))
        .options(selectinload(Category.translations))
        .order_by(Category.order.asc())
    )
    grouped: dict[int, list[Category]] = defaultdict(list)
    for category in result.scalars().all():
        grouped[category.parent_id].append(category)
    return grouped


async def color_by_category(db: AsyncSession) -> dict[int, str | None]:
    result = await db.execute(select(TrendCategory.category_id, TrendCategory.color))
    colors: dict[int, str | None] = {}
    for category_id, color in result.all():
        colors.setdefault(category_id, color)
    return colors


async def list_trend(db: AsyncSession) -> list[tuple[TrendCategory, Category]]:
    result = await db.execute(
        select(TrendCategory, Category)
        .join(Category, TrendCategory.category_id == Category.id)
        .options(selectinload(Category.translations))
        .order_by(TrendCategory.created_at.desc())
    )
    return [(tc, cat) for tc, cat in result.all()]
