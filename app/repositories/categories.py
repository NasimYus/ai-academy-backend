import re
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category, TrendCategory


async def list_all(db: AsyncSession) -> list[Category]:
    """Every category (incl. disabled + sub-categories), for admin management."""
    result = await db.execute(select(Category).order_by(Category.order.asc(), Category.id.asc()))
    return list(result.scalars().all())


async def get(db: AsyncSession, category_id: int) -> Category | None:
    return await db.get(Category, category_id)


async def unique_slug(db: AsyncSession, title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "category"
    candidate, i = base, 2
    while (await db.execute(select(Category.id).where(Category.slug == candidate))).first():
        candidate = f"{base}-{i}"
        i += 1
    return candidate


async def create(db: AsyncSession, data: dict) -> Category:
    category = Category(**data)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update(db: AsyncSession, category: Category, changes: dict) -> Category:
    for key, value in changes.items():
        setattr(category, key, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete(db: AsyncSession, category: Category) -> None:
    await db.delete(category)
    await db.commit()


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
