from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.featured_course import FeaturedCourse, FeaturedPage, FeaturedStatus


async def _seed() -> None:
    async with AsyncSessionLocal() as db:
        featured = Course(
            title="Featured",
            slug="feat",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        pending = Course(
            title="Pending Feature",
            slug="pend",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        other_page = Course(
            title="Sidebar",
            slug="side",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add_all([featured, pending, other_page])
        await db.flush()
        db.add_all(
            [
                FeaturedCourse(
                    course_id=featured.id, page=FeaturedPage.home, status=FeaturedStatus.publish
                ),
                FeaturedCourse(
                    course_id=pending.id, page=FeaturedPage.home, status=FeaturedStatus.pending
                ),  # not published
                FeaturedCourse(
                    course_id=other_page.id,
                    page=FeaturedPage.categories,
                    status=FeaturedStatus.publish,
                ),  # wrong page
            ]
        )
        await db.commit()


async def test_featured_only_published_home(client: AsyncClient):
    await _seed()
    r = await client.get("/api/v1/featured-courses")
    assert r.status_code == 200
    assert [c["slug"] for c in r.json()] == ["feat"]


async def test_featured_empty(client: AsyncClient):
    r = await client.get("/api/v1/featured-courses")
    assert r.status_code == 200
    assert r.json() == []
