"""Rewards/points — parity of RewardsController + RewardAccounting.

The whole subsystem is gated by `settings.rewards_status` (legacy
getRewardsSettings()['status']); off by default → endpoints 404/403 and
`record` is a no-op, exactly like a clean legacy DB. Earning rules (the
`Reward` table wired into events) are deferred — points can still be granted
via `record` and spent via redeem/exchange.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.reward import RewardAccounting, RewardStatus
from app.models.user import User
from app.repositories import rewards as rewards_repo
from app.schemas.reward import LeaderUser, RewardEntry, RewardsOverview
from app.schemas.user import UserBrief


def enabled() -> bool:
    return settings.rewards_status


async def record(
    db: AsyncSession,
    *,
    user_id: int,
    score: int,
    type: str,
    status: RewardStatus = RewardStatus.addiction,
    item_id: int | None = None,
    commit: bool = True,
) -> RewardAccounting | None:
    """Write a ledger entry, honoring the gate (legacy makeRewardAccounting)."""
    if not enabled() or score <= 0:
        return None
    return await rewards_repo.create_entry(
        db, user_id=user_id, score=score, type=type, status=status, item_id=item_id, commit=commit
    )


def _entry(e: RewardAccounting) -> RewardEntry:
    return RewardEntry(
        id=e.id,
        user=UserBrief.model_validate(e.user),
        item_id=e.item_id,
        type=e.type,
        score=e.score,
        status="addition" if e.status == RewardStatus.addiction else e.status.value,
        created_at=e.created_at,
    )


async def build_overview(db: AsyncSession, user: User) -> RewardsOverview:
    pts = await rewards_repo.points(db, user.id)
    entries = await rewards_repo.history(db, user.id)

    board_rows = await rewards_repo.leaderboard(db)
    users = {}
    if board_rows:
        result = await db.execute(select(User).where(User.id.in_([uid for uid, _ in board_rows])))
        users = {u.id: u for u in result.scalars().all()}
    leaders = [
        LeaderUser(user=UserBrief.model_validate(users[uid]), total_points=total)
        for uid, total in board_rows
        if uid in users
    ]

    earn_by_exchange = 0
    if settings.rewards_exchangeable and settings.rewards_exchangeable_unit:
        earn_by_exchange = pts["available"] // settings.rewards_exchangeable_unit

    return RewardsOverview(
        available_points=pts["available"],
        total_points=pts["total"],
        spent_points=pts["spent"],
        rewards=[_entry(e) for e in entries],
        exchangeable=1 if settings.rewards_exchangeable else 0,
        earn_by_exchange=earn_by_exchange,
        leader_board=leaders[0] if leaders else None,
        most_points_users=leaders[1:],
    )
