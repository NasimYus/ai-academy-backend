from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meeting import (
    DayLabel,
    Meeting,
    MeetingTime,
    ReserveMeeting,
    ReserveStatus,
)

_RESERVE_LOADS = (
    selectinload(ReserveMeeting.meeting).selectinload(Meeting.creator),
    selectinload(ReserveMeeting.meeting).selectinload(Meeting.times),
    selectinload(ReserveMeeting.meeting_time),
    selectinload(ReserveMeeting.user),
)


# --- instructor meeting config ---


async def get_meeting_for_creator(db: AsyncSession, creator_id: int) -> Meeting | None:
    result = await db.execute(
        select(Meeting).where(Meeting.creator_id == creator_id).options(selectinload(Meeting.times))
    )
    return result.scalar_one_or_none()


async def get_or_create_meeting(db: AsyncSession, creator_id: int) -> Meeting:
    meeting = await get_meeting_for_creator(db, creator_id)
    if meeting is None:
        meeting = Meeting(creator_id=creator_id)
        db.add(meeting)
        await db.commit()
        meeting = await get_meeting_for_creator(db, creator_id)
    return meeting  # type: ignore[return-value]


async def update_meeting(db: AsyncSession, meeting: Meeting, changes: dict) -> Meeting:
    for key, value in changes.items():
        setattr(meeting, key, value)
    await db.commit()
    return await get_meeting_for_creator(db, meeting.creator_id)  # type: ignore[return-value]


async def add_time(
    db: AsyncSession, *, meeting_id: int, day_label: DayLabel, time: str
) -> MeetingTime:
    slot = MeetingTime(meeting_id=meeting_id, day_label=day_label, time=time)
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


async def get_time_owned(db: AsyncSession, time_id: int, creator_id: int) -> MeetingTime | None:
    result = await db.execute(
        select(MeetingTime)
        .join(Meeting, Meeting.id == MeetingTime.meeting_id)
        .where(MeetingTime.id == time_id, Meeting.creator_id == creator_id)
    )
    return result.scalar_one_or_none()


async def delete_time(db: AsyncSession, slot: MeetingTime) -> None:
    await db.delete(slot)
    await db.commit()


# --- booking ---


async def get_meeting_with_times(db: AsyncSession, meeting_id: int) -> Meeting | None:
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id).options(selectinload(Meeting.times))
    )
    return result.scalar_one_or_none()


async def get_instructor_meeting(db: AsyncSession, instructor_id: int) -> Meeting | None:
    """An instructor's enabled meeting config + slots (for booking)."""
    result = await db.execute(
        select(Meeting)
        .where(Meeting.creator_id == instructor_id, Meeting.disabled.is_(False))
        .options(selectinload(Meeting.times))
    )
    return result.scalar_one_or_none()


async def get_time(db: AsyncSession, time_id: int) -> MeetingTime | None:
    return await db.get(MeetingTime, time_id)


async def create_reservation(db: AsyncSession, reserve: ReserveMeeting) -> ReserveMeeting:
    db.add(reserve)
    await db.commit()
    result = await db.execute(
        select(ReserveMeeting).where(ReserveMeeting.id == reserve.id).options(*_RESERVE_LOADS)
    )
    return result.scalar_one()


async def reservations_for_user(db: AsyncSession, user_id: int) -> list[ReserveMeeting]:
    result = await db.execute(
        select(ReserveMeeting)
        .where(ReserveMeeting.user_id == user_id)
        .options(*_RESERVE_LOADS)
        .order_by(ReserveMeeting.created_at.desc())
    )
    return list(result.scalars().all())


async def requests_for_creator(db: AsyncSession, creator_id: int) -> list[ReserveMeeting]:
    meeting_ids = select(Meeting.id).where(Meeting.creator_id == creator_id)
    result = await db.execute(
        select(ReserveMeeting)
        .where(ReserveMeeting.meeting_id.in_(meeting_ids))
        .options(*_RESERVE_LOADS)
        .order_by(ReserveMeeting.created_at.desc())
    )
    return list(result.scalars().all())


async def get_reservation_participant(
    db: AsyncSession, reserve_id: int, user_id: int
) -> ReserveMeeting | None:
    """A reservation the user booked, or one on a meeting they own."""
    owned_meetings = select(Meeting.id).where(Meeting.creator_id == user_id)
    result = await db.execute(
        select(ReserveMeeting)
        .where(
            ReserveMeeting.id == reserve_id,
            or_(
                ReserveMeeting.user_id == user_id,
                ReserveMeeting.meeting_id.in_(owned_meetings),
            ),
        )
        .options(*_RESERVE_LOADS)
    )
    return result.scalar_one_or_none()


async def set_status(
    db: AsyncSession, reserve: ReserveMeeting, status: ReserveStatus
) -> ReserveMeeting:
    reserve.status = status
    await db.commit()
    return reserve
