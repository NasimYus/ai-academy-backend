"""Presenters mapping Meeting/ReserveMeeting rows to API schemas.

Relationships are eager-loaded by the repository (lazy="raise").
"""

from app.models.meeting import Meeting, ReserveMeeting
from app.schemas.meeting import (
    MeetingConfig,
    MeetingTimeRead,
    ReserveMeetingRead,
    TimeRange,
)
from app.schemas.user import UserBrief


def meeting_config(meeting: Meeting) -> MeetingConfig:
    return MeetingConfig(
        id=meeting.id,
        amount=meeting.amount,
        discount=meeting.discount,
        disabled=meeting.disabled,
        times=[MeetingTimeRead(id=t.id, day_label=t.day_label, time=t.time) for t in meeting.times],
    )


def _time_range(raw: str) -> TimeRange | None:
    parts = raw.split("-")
    if len(parts) != 2:
        return None
    return TimeRange(start=parts[0].strip(), end=parts[1].strip())


def reserve_detail(reserve: ReserveMeeting) -> ReserveMeetingRead:
    slot = reserve.meeting_time
    instructor = reserve.meeting.creator if reserve.meeting else None
    return ReserveMeetingRead(
        id=reserve.id,
        status=reserve.status,
        link=reserve.link,
        amount=reserve.paid_amount,
        discount=reserve.discount,
        date=reserve.date,
        day=slot.day_label if slot else None,
        time=_time_range(slot.time) if slot else None,
        student_count=reserve.student_count,
        description=reserve.description,
        meeting=meeting_config(reserve.meeting),
        instructor=UserBrief.model_validate(instructor) if instructor else None,
        type=reserve.meeting_type,
        can_agora=False,  # NOTE(Phase 7): agora_for_meeting gated/deferred
    )
