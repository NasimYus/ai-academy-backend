from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discount import Discount, DiscountCategory, DiscountCourse, DiscountUser


async def get_by_code(db: AsyncSession, code: str) -> Discount | None:
    result = await db.execute(select(Discount).where(Discount.code == code))
    return result.scalar_one_or_none()


async def course_ids(db: AsyncSession, discount_id: int) -> set[int]:
    result = await db.execute(
        select(DiscountCourse.course_id).where(DiscountCourse.discount_id == discount_id)
    )
    return set(result.scalars().all())


async def category_ids(db: AsyncSession, discount_id: int) -> set[int]:
    result = await db.execute(
        select(DiscountCategory.category_id).where(DiscountCategory.discount_id == discount_id)
    )
    return set(result.scalars().all())


async def user_whitelisted(db: AsyncSession, discount_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(DiscountUser.id).where(
            DiscountUser.discount_id == discount_id, DiscountUser.user_id == user_id
        )
    )
    return result.first() is not None
