from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DbSession, require_level
from app.models.meeting import ReserveMeeting, ReserveStatus
from app.models.user import User
from app.repositories import meetings as meetings_repo
from app.repositories import orders as orders_repo
from app.schemas.common import error_responses
from app.schemas.meeting import (
    MeetingConfig,
    MeetingConfigInput,
    MeetingTimeInput,
    MeetingTimeRead,
    ReserveBucket,
    ReserveCreate,
    ReserveIndex,
    ReserveMeetingRead,
)
from app.schemas.order import OrderRead
from app.services import meeting_presenter
from app.services.order_presenter import order_read

router = APIRouter(tags=["meetings"])

TeacherUser = Annotated[User, Depends(require_level("teacher"))]


# --- instructor: meeting config + availability (legacy ReserveMeeting setup) ---


@router.get(
    "/panel/meeting",
    response_model=MeetingConfig,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def my_meeting(current_user: TeacherUser, db: DbSession) -> MeetingConfig:
    """The instructor's consultation config + slots (created on first access)."""
    meeting = await meetings_repo.get_or_create_meeting(db, current_user.id)
    return meeting_presenter.meeting_config(meeting)


@router.put(
    "/panel/meeting",
    response_model=MeetingConfig,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def update_my_meeting(
    payload: MeetingConfigInput, current_user: TeacherUser, db: DbSession
) -> MeetingConfig:
    """Set price/discount and enable/disable consultations."""
    meeting = await meetings_repo.get_or_create_meeting(db, current_user.id)
    meeting = await meetings_repo.update_meeting(db, meeting, payload.model_dump())
    return meeting_presenter.meeting_config(meeting)


@router.post(
    "/panel/meeting/times",
    response_model=MeetingTimeRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def add_meeting_time(
    payload: MeetingTimeInput, current_user: TeacherUser, db: DbSession
) -> MeetingTimeRead:
    meeting = await meetings_repo.get_or_create_meeting(db, current_user.id)
    slot = await meetings_repo.add_time(
        db, meeting_id=meeting.id, day_label=payload.day_label, time=payload.time
    )
    return MeetingTimeRead(id=slot.id, day_label=slot.day_label, time=slot.time)


@router.delete(
    "/panel/meeting/times/{time_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def delete_meeting_time(time_id: int, current_user: TeacherUser, db: DbSession) -> None:
    slot = await meetings_repo.get_time_owned(db, time_id, current_user.id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")
    await meetings_repo.delete_time(db, slot)


# --- public: an instructor's bookable availability ---


@router.get(
    "/users/{instructor_id}/meeting",
    response_model=MeetingConfig | None,
)
async def instructor_meeting(instructor_id: int, db: DbSession) -> MeetingConfig | None:
    """An instructor's enabled consultation config (null if none/disabled)."""
    meeting = await meetings_repo.get_instructor_meeting(db, instructor_id)
    return meeting_presenter.meeting_config(meeting) if meeting else None


# --- user: reservations ---


@router.post(
    "/meetings/reserve",
    response_model=ReserveMeetingRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND
    ),
)
async def reserve_meeting(
    payload: ReserveCreate, current_user: CurrentUser, db: DbSession
) -> ReserveMeetingRead:
    """Reserve an instructor's slot. NOTE(Phase 7): paid checkout/Agora gated —
    reservation is created directly (free path)."""
    slot = await meetings_repo.get_time(db, payload.meeting_time_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")
    meeting = await meetings_repo.get_meeting_with_times(db, slot.meeting_id)
    if meeting is None or meeting.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="meeting_unavailable")
    if meeting.creator_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot_reserve_own")

    reserve = ReserveMeeting(
        meeting_id=meeting.id,
        meeting_time_id=slot.id,
        user_id=current_user.id,
        day=slot.day_label.value,
        date=payload.date,
        status=ReserveStatus.pending,
        paid_amount=meeting.amount or 0,
        meeting_type=payload.meeting_type,
        student_count=payload.student_count,
        description=payload.description,
        reserved_at=payload.date,
    )
    reserve = await meetings_repo.create_reservation(db, reserve)
    return meeting_presenter.reserve_detail(reserve)


@router.post(
    "/meetings/reserve/{reserve_id}/pay",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def pay_reservation(reserve_id: int, current_user: CurrentUser, db: DbSession) -> OrderRead:
    """Create a pending order for a paid reservation (legacy reserve → checkout).

    Settling it via /payments links the Sale to the reservation, stamps
    `reserved_at`, and opens it (`payments._confirm_reservation`)."""
    reservation = await db.get(ReserveMeeting, reserve_id)
    if reservation is None or reservation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.sale_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="already_paid"
        )
    amount = float(reservation.paid_amount or 0)
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_free")

    order = await orders_repo.create(
        db,
        user_id=current_user.id,
        amount=amount,
        total_discount=0,
        total_amount=amount,
        items=[{"reserve_meeting_id": reserve_id, "amount": amount, "total_amount": amount}],
    )
    return order_read(order)


@router.get(
    "/panel/meetings",
    response_model=ReserveIndex,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def meetings_index(current_user: CurrentUser, db: DbSession) -> ReserveIndex:
    """My reservations + requests on my meetings (legacy ReserveMeetingsController@index)."""
    reservations = await meetings_repo.reservations_for_user(db, current_user.id)
    requests = await meetings_repo.requests_for_creator(db, current_user.id)
    return ReserveIndex(
        reservations=ReserveBucket(
            count=len(reservations),
            meetings=[meeting_presenter.reserve_detail(r) for r in reservations],
        ),
        requests=ReserveBucket(
            count=len(requests),
            meetings=[meeting_presenter.reserve_detail(r) for r in requests],
        ),
    )


@router.get(
    "/panel/meetings/{reserve_id}",
    response_model=ReserveMeetingRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def show_reservation(
    reserve_id: int, current_user: CurrentUser, db: DbSession
) -> ReserveMeetingRead:
    reserve = await meetings_repo.get_reservation_participant(db, reserve_id, current_user.id)
    if reserve is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return meeting_presenter.reserve_detail(reserve)


@router.post(
    "/panel/meetings/{reserve_id}/finish",
    response_model=ReserveMeetingRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def finish_reservation(
    reserve_id: int, current_user: CurrentUser, db: DbSession
) -> ReserveMeetingRead:
    """Mark a reservation finished (legacy @finish; either participant)."""
    reserve = await meetings_repo.get_reservation_participant(db, reserve_id, current_user.id)
    if reserve is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    reserve = await meetings_repo.set_status(db, reserve, ReserveStatus.finished)
    return meeting_presenter.reserve_detail(reserve)
