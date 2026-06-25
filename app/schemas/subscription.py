from pydantic import BaseModel

# Parity of legacy Subscribe::details + Web\SubscribesController@list.


class SubscribePlan(BaseModel):
    id: int
    title: str
    usable_count: int
    days: int
    price: float
    icon: str | None = None
    description: str | None = None


class ActiveSubscription(BaseModel):
    id: int  # plan id
    title: str
    usable_count: int
    used_count: int
    remaining: int
    days: int
    days_left: int


class SubscribeList(BaseModel):
    count: int
    subscribes: list[SubscribePlan]
    subscribed: ActiveSubscription | None = None
    day_of_use: int | None = None


class SubscribeApplyRequest(BaseModel):
    course_id: int


class SubscribeResponse(BaseModel):
    message: str
