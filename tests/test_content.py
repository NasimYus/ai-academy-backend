from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.content import Accessibility, Chapter, File, TextLesson
from app.models.course import Course, CourseStatus, CourseType
from tests.conftest import register_verified_user


async def _seed_course_with_content() -> str:
    async with AsyncSessionLocal() as db:
        course = Course(
            title="Content Course",
            slug="content-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add(course)
        await db.flush()
        chapter = Chapter(course_id=course.id, title="Chapter 1", order=1)
        db.add(chapter)
        await db.flush()
        db.add_all(
            [
                TextLesson(
                    course_id=course.id,
                    chapter_id=chapter.id,
                    title="Free Intro",
                    summary="intro",
                    content="full content",
                    accessibility=Accessibility.free,
                    order=1,
                ),
                File(
                    course_id=course.id,
                    chapter_id=chapter.id,
                    title="Paid PDF",
                    accessibility=Accessibility.paid,
                    file="/media/x.pdf",
                    file_type="pdf",
                    order=2,
                ),
                File(
                    course_id=course.id,
                    chapter_id=None,
                    title="Top-level paid",
                    accessibility=Accessibility.paid,
                    file="/media/top.pdf",
                    order=1,
                ),
            ]
        )
        await db.commit()
        return course.slug


async def test_content_anonymous_locks_paid_reveals_free(client: AsyncClient):
    slug = await _seed_course_with_content()
    r = await client.get(f"/api/v1/courses/{slug}/content")
    assert r.status_code == 200
    body = r.json()
    assert body["has_access"] is False

    chapter = body["chapters"][0]
    items = {i["title"]: i for i in chapter["items"]}
    # free text lesson: unlocked, content present
    assert items["Free Intro"]["locked"] is False
    assert items["Free Intro"]["content"] == "full content"
    # paid file: locked, file path withheld but preview (file_type) kept
    assert items["Paid PDF"]["locked"] is True
    assert items["Paid PDF"]["file"] is None
    assert items["Paid PDF"]["file_type"] == "pdf"
    # top-level item present
    assert len(body["items"]) == 1
    assert body["items"][0]["locked"] is True


async def test_content_enrolled_unlocks_paid(client: AsyncClient):
    slug = await _seed_course_with_content()
    token, _ = await register_verified_user(client, "c@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}

    # course id 1 (first seeded); enroll free
    await client.post("/api/v1/panel/courses/1/free", headers=headers)

    r = await client.get(f"/api/v1/courses/{slug}/content", headers=headers)
    body = r.json()
    assert body["has_access"] is True
    items = {i["title"]: i for i in body["chapters"][0]["items"]}
    assert items["Paid PDF"]["locked"] is False
    assert items["Paid PDF"]["file"] == "/media/x.pdf"


async def test_content_404(client: AsyncClient):
    r = await client.get("/api/v1/courses/nope/content")
    assert r.status_code == 404
