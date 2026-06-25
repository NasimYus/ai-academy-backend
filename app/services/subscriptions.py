"""Subscriptions — parity of Subscribe::getActiveSubscribe + SubscribesController@apply.

An activated subscription is "active" while it is within its `days` window and
still has unused capacity (`used_count < usable_count`). Applying it to a
subscribable course unlocks access (enrollment, source=subscribe).
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscribe, UserSubscribe
from app.repositories import subscriptions as subs_repo
from app.schemas.subscription import ActiveSubscription


@dataclass
class ActiveState:
    user_subscribe: UserSubscribe
    plan: Subscribe
    used_count: int
    days_used: int
    remaining: int


async def get_active(db: AsyncSession, user_id: int) -> ActiveState | None:
    latest = await subs_repo.latest_user_subscribe(db, user_id)
    if latest is None:
        return None
    plan = latest.subscribe
    days_used = (datetime.now(UTC) - latest.created_at).days
    used_count = await subs_repo.count_uses(db, user_id, plan.id)
    if plan.days < days_used or used_count >= plan.usable_count:
        return None
    return ActiveState(
        user_subscribe=latest,
        plan=plan,
        used_count=used_count,
        days_used=days_used,
        remaining=plan.usable_count - used_count,
    )


def to_active_schema(state: ActiveState) -> ActiveSubscription:
    return ActiveSubscription(
        id=state.plan.id,
        title=state.plan.title,
        usable_count=state.plan.usable_count,
        used_count=state.used_count,
        remaining=state.remaining,
        days=state.plan.days,
        days_left=state.plan.days - state.days_used,
    )
