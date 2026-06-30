from datetime import datetime

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    """One dated item on the student's events calendar (legacy
    EventsCalendarController event entry). `type` is the legacy event group key
    (e.g. ``meetings``, ``live_class_start``, ``courses_expirations``)."""

    type: str
    subtitle: str
    event_at: datetime
    time: str | None = None


class EventsCalendar(BaseModel):
    """All upcoming events for the current user. The client derives the calendar
    dots, per-day list and the upcoming panel from this flat list."""

    events: list[CalendarEvent]
    total: int
