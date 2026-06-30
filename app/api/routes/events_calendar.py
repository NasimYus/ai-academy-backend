from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import error_responses
from app.schemas.events_calendar import EventsCalendar
from app.services import events_calendar as events_service

router = APIRouter(prefix="/panel", tags=["events-calendar"])


@router.get(
    "/events-calendar",
    response_model=EventsCalendar,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def events_calendar(current_user: CurrentUser, db: DbSession) -> EventsCalendar:
    """Upcoming events for the panel calendar (legacy EventsCalendarController).
    Returns a flat, date-sorted list; the client derives day/upcoming views."""
    events = await events_service.upcoming_events(db, current_user)
    return EventsCalendar(events=events, total=len(events))
