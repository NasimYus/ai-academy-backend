from datetime import datetime

from pydantic import BaseModel, Field

from app.models.meeting import DayLabel, ReserveMeetingType, ReserveStatus
from app.schemas.user import UserBrief


class MeetingTimeRead(BaseModel):
    id: int
    day_label: DayLabel
    time: str


class MeetingConfig(BaseModel):
    id: int
    amount: int | None
    discount: int | None
    disabled: bool
    times: list[MeetingTimeRead]


class MeetingConfigInput(BaseModel):
    amount: int | None = None
    discount: int | None = None
    disabled: bool = False


class MeetingTimeInput(BaseModel):
    day_label: DayLabel
    time: str = Field(min_length=1, max_length=64)


class TimeRange(BaseModel):
    start: str
    end: str


class ReserveMeetingRead(BaseModel):
    id: int
    status: ReserveStatus
    link: str | None
    amount: int
    discount: int | None
    date: datetime | None
    day: DayLabel | None
    time: TimeRange | None
    student_count: int | None
    description: str | None
    meeting: MeetingConfig
    instructor: UserBrief | None  # legacy `user` = the meeting's creator
    type: ReserveMeetingType
    can_agora: bool  # gated (agora_for_meeting) — always false here


class ReserveBucket(BaseModel):
    count: int
    meetings: list[ReserveMeetingRead]


class ReserveIndex(BaseModel):
    reservations: ReserveBucket
    requests: ReserveBucket


class ReserveCreate(BaseModel):
    meeting_time_id: int
    date: datetime | None = None
    description: str | None = None
    student_count: int | None = None
    meeting_type: ReserveMeetingType = ReserveMeetingType.online
