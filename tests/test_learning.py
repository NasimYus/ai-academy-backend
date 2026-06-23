from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.content import Accessibility, Chapter, File, TextLesson
from app.models.course import Course, CourseStatus, CourseType
from tests.conftest import register_verified_user


async def _seed_course_with_content() -> tuple[int, str, int, int]:
    """Returns (course_id, slug, file_id, text_lesson_id)."""
    async with AsyncSessionLocal() as db:
        course = Course(
            title="Learn Course",
            slug="learn-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add(course)
        await db.flush()
        chapter = Chapter(course_id=course.id, title="Chapter 1", order=1)
        db.add(chapter)
        await db.flush()
        lesson = TextLesson(
            course_id=course.id,
            chapter_id=chapter.id,
            title="Free Intro",
            summary="intro",
            content="full content",
            accessibility=Accessibility.free,
            order=1,
        )
        pdf = File(
            course_id=course.id,
            chapter_id=chapter.id,
            title="Paid PDF",
            accessibility=Accessibility.paid,
            file="/media/x.pdf",
            file_type="pdf",
            order=2,
        )
        db.add_all([lesson, pdf])
        await db.commit()
        return course.id, course.slug, pdf.id, lesson.id


async def _enroll(client: AsyncClient, headers: dict, course_id: int) -> None:
    await client.post(f"/api/v1/panel/courses/{course_id}/free", headers=headers)


async def test_toggle_marks_and_reflects_in_content(client: AsyncClient):
    course_id, slug, file_id, lesson_id = await _seed_course_with_content()
    token, _ = await register_verified_user(client, "l@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    await _enroll(client, headers, course_id)

    # mark the text lesson learned
    r = await client.post(
        f"/api/v1/courses/{course_id}/learning",
        headers=headers,
        json={"item_type": "text_lesson", "item_id": lesson_id, "learned": True},
    )
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "learned": True}

    # content reflects completed for this user only
    r = await client.get(f"/api/v1/courses/{slug}/content", headers=headers)
    items = {i["title"]: i for i in r.json()["chapters"][0]["items"]}
    assert items["Free Intro"]["completed"] is True
    assert items["Paid PDF"]["completed"] is False


async def test_toggle_unmarks(client: AsyncClient):
    course_id, slug, file_id, lesson_id = await _seed_course_with_content()
    token, _ = await register_verified_user(client, "l2@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    await _enroll(client, headers, course_id)

    body = {"item_type": "file", "item_id": file_id, "learned": True}
    await client.post(f"/api/v1/courses/{course_id}/learning", headers=headers, json=body)
    # now unmark
    body["learned"] = False
    r = await client.post(f"/api/v1/courses/{course_id}/learning", headers=headers, json=body)
    assert r.json()["learned"] is False

    r = await client.get(f"/api/v1/courses/{slug}/content", headers=headers)
    items = {i["title"]: i for i in r.json()["chapters"][0]["items"]}
    assert items["Paid PDF"]["completed"] is False


async def test_toggle_requires_access(client: AsyncClient):
    course_id, _, _, lesson_id = await _seed_course_with_content()
    token, _ = await register_verified_user(client, "l3@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    # not enrolled
    r = await client.post(
        f"/api/v1/courses/{course_id}/learning",
        headers=headers,
        json={"item_type": "text_lesson", "item_id": lesson_id, "learned": True},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "not_purchased"


async def test_toggle_requires_auth(client: AsyncClient):
    course_id, _, _, lesson_id = await _seed_course_with_content()
    r = await client.post(
        f"/api/v1/courses/{course_id}/learning",
        json={"item_type": "text_lesson", "item_id": lesson_id, "learned": True},
    )
    assert r.status_code == 401


async def test_toggle_course_404(client: AsyncClient):
    token, _ = await register_verified_user(client, "l4@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/courses/999/learning",
        headers=headers,
        json={"item_type": "text_lesson", "item_id": 1, "learned": True},
    )
    assert r.status_code == 404


async def test_toggle_item_not_in_course_404(client: AsyncClient):
    course_id, _, _, _ = await _seed_course_with_content()
    token, _ = await register_verified_user(client, "l5@aiacademy.tj")
    headers = {"Authorization": f"Bearer {token}"}
    await _enroll(client, headers, course_id)
    r = await client.post(
        f"/api/v1/courses/{course_id}/learning",
        headers=headers,
        json={"item_type": "text_lesson", "item_id": 9999, "learned": True},
    )
    assert r.status_code == 404
