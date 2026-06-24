from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserBrief

# Parity with legacy Api\RewardAccounting + RewardsController@index.


class RewardEntry(BaseModel):
    id: int
    user: UserBrief
    item_id: int | None = None
    type: str
    score: int
    # legacy maps ADDICTION -> 'addition' in the API payload
    status: str
    created_at: datetime


class LeaderUser(BaseModel):
    user: UserBrief
    total_points: int


class RewardsOverview(BaseModel):
    available_points: int
    total_points: int
    spent_points: int
    rewards: list[RewardEntry]
    exchangeable: int
    earn_by_exchange: int
    leader_board: LeaderUser | None = None
    most_points_users: list[LeaderUser] = []


class RedeemResponse(BaseModel):
    message: str
