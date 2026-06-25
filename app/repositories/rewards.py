from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reward import Reward, RewardAccounting, RewardStatus, RewardType


async def get_active_rule(db: AsyncSession, reward_type: RewardType) -> Reward | None:
    """The enabled earning rule for an event type (legacy Reward::where(type))."""
    result = await db.execute(
        select(Reward).where(Reward.type == reward_type, Reward.enabled.is_(True))
    )
    return result.scalars().first()


async def entry_exists(
    db: AsyncSession,
    *,
    user_id: int,
    type: str,
    item_id: int | None,
    status: RewardStatus = RewardStatus.addiction,
) -> bool:
    """Legacy checkDuplicate: one award per user+item+type+status."""
    result = await db.execute(
        select(RewardAccounting.id).where(
            RewardAccounting.user_id == user_id,
            RewardAccounting.type == type,
            RewardAccounting.item_id == item_id,
            RewardAccounting.status == status,
        )
    )
    return result.first() is not None


async def _sum(db: AsyncSession, user_id: int, status: RewardStatus) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(RewardAccounting.score), 0)).where(
            RewardAccounting.user_id == user_id, RewardAccounting.status == status
        )
    )
    return int(result.scalar_one())


async def points(db: AsyncSession, user_id: int) -> dict[str, int]:
    """Earned / spent / available points for a user (legacy getRewardPoints)."""
    earned = await _sum(db, user_id, RewardStatus.addiction)
    spent = await _sum(db, user_id, RewardStatus.deduction)
    return {"total": earned, "spent": spent, "available": earned - spent}


async def history(db: AsyncSession, user_id: int) -> list[RewardAccounting]:
    result = await db.execute(
        select(RewardAccounting)
        .where(RewardAccounting.user_id == user_id)
        .options(selectinload(RewardAccounting.user))
        .order_by(RewardAccounting.created_at.desc())
    )
    return list(result.scalars().all())


async def leaderboard(db: AsyncSession, limit: int = 4) -> list[tuple[int, int]]:
    """Top users by earned points (legacy: most points). Returns (user_id, total)."""
    total = func.coalesce(func.sum(RewardAccounting.score), 0).label("total")
    result = await db.execute(
        select(RewardAccounting.user_id, total)
        .where(RewardAccounting.status == RewardStatus.addiction)
        .group_by(RewardAccounting.user_id)
        .order_by(total.desc())
        .limit(limit)
    )
    return [(uid, int(t)) for uid, t in result.all()]


async def create_entry(
    db: AsyncSession,
    *,
    user_id: int,
    score: int,
    type: str,
    status: RewardStatus,
    item_id: int | None = None,
    commit: bool = True,
) -> RewardAccounting:
    entry = RewardAccounting(
        user_id=user_id, score=score, type=type, status=status, item_id=item_id
    )
    db.add(entry)
    if commit:
        await db.commit()
        await db.refresh(entry)
    return entry
