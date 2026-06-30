from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment, EnrollmentSource
from tests.conftest import register_verified_user


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_events_calendar_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/panel/events-calendar")
    assert r.status_code == 401


async def test_events_calendar_empty_for_fresh_student(client: AsyncClient):
    token, _ = await register_verified_user(client, email="evcal-empty@aiacademy.tj")
    r = await client.get("/api/v1/panel/events-calendar", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body == {"events": [], "total": 0}


async def test_events_calendar_surfaces_upcoming_live_class(client: AsyncClient):
    token, uid = await register_verified_user(client, email="evcal-live@aiacademy.tj")
    start = datetime.now(UTC) + timedelta(days=3)
    async with AsyncSessionLocal() as db:
        course = Course(
            title="Live AI",
            slug="evcal-live-ai",
            type=CourseType.webinar,
            status=CourseStatus.active,
            price=10,
            start_date=start,
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        db.add(Enrollment(user_id=uid, course_id=course.id, source=EnrollmentSource.free))
        await db.commit()

    r = await client.get("/api/v1/panel/events-calendar", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["events"][0]["type"] == "live_class_start"
    assert body["events"][0]["subtitle"] == "Live AI"
