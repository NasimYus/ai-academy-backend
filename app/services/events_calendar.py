"""Events calendar aggregation (parity of legacy Panel\\EventsCalendarController).

Legacy aggregates eleven event groups; the ones whose subsystems are migrated and
carry a reliable date are computed here:

* ``meetings``          — the student's future meeting reservations
* ``live_class_start``  — enrolled live (webinar) courses with a future start date
* ``courses_expirations`` — enrolled courses with ``access_days``, expiry derived
                            from the buyer's sale date (created_at + access_days)

The remaining groups (quiz/assignment deadlines, bundle/subscription/registration
package/installment expirations, live_sessions, ticketed events) depend on
subsystems not yet migrated or on per-user deadline derivation — gated to empty on
a clean DB, exactly as legacy renders them. NOTE(Phase): wire as those land.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import CourseType
from app.models.meeting import ReserveStatus
from app.models.user import User
from app.repositories import enrollments as enrollments_repo
from app.repositories import meetings as meetings_repo
from app.repositories import sales as sales_repo
from app.schemas.events_calendar import CalendarEvent


async def upcoming_events(db: AsyncSession, user: User) -> list[CalendarEvent]:
    now = datetime.now(UTC)
    events: list[CalendarEvent] = []

    # Meetings — reservations the student booked, still upcoming.
    for reserve in await meetings_repo.reservations_for_user(db, user.id):
        if reserve.date and reserve.date > now and reserve.status != ReserveStatus.canceled:
            creator = reserve.meeting.creator if reserve.meeting else None
            events.append(
                CalendarEvent(
                    type="meetings",
                    subtitle=creator.full_name if creator else "—",
                    event_at=reserve.date,
                    time=reserve.date.strftime("%H:%M"),
                )
            )

    # Course-derived events (live class start + access expiration).
    courses = await enrollments_repo.list_courses_for_user(db, user.id)
    sale_date_by_course: dict[int, datetime] = {}
    for sale in await sales_repo.buyer_sales(db, user.id):
        if sale.course_id and sale.course_id not in sale_date_by_course:
            sale_date_by_course[sale.course_id] = sale.created_at

    for course in courses:
        if course.type == CourseType.webinar and course.start_date and course.start_date > now:
            events.append(
                CalendarEvent(
                    type="live_class_start",
                    subtitle=course.title,
                    event_at=course.start_date,
                    time=course.start_date.strftime("%H:%M"),
                )
            )
        if course.access_days:
            started = sale_date_by_course.get(course.id)
            if started:
                expire_at = started + timedelta(days=course.access_days)
                if expire_at > now:
                    events.append(
                        CalendarEvent(
                            type="courses_expirations",
                            subtitle=course.title,
                            event_at=expire_at,
                        )
                    )

    events.sort(key=lambda e: e.event_at)
    return events
