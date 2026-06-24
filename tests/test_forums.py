from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from tests.conftest import register_verified_user


async def _course_owned_by(owner_id: int) -> int:
    async with AsyncSessionLocal() as db:
        course = Course(
            title="Forum Course",
            slug="forum-course",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
            creator_id=owner_id,
            teacher_id=owner_id,
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course.id


async def _setup(client: AsyncClient):
    """Owner (course creator) + enrolled student. Returns (course_id, owner_h, student_h)."""
    owner_token, owner_id = await register_verified_user(client, "fo-owner@aiacademy.tj")
    owner_h = {"Authorization": f"Bearer {owner_token}"}
    course_id = await _course_owned_by(owner_id)

    student_token, _ = await register_verified_user(client, "fo-student@aiacademy.tj")
    student_h = {"Authorization": f"Bearer {student_token}"}
    await client.post(f"/api/v1/panel/courses/{course_id}/free", headers=student_h)
    return course_id, owner_h, student_h


async def _create_thread(client: AsyncClient, course_id: int, headers: dict) -> int:
    r = await client.post(
        f"/api/v1/courses/{course_id}/forums",
        headers=headers,
        data={"title": "How do I X?", "description": "stuck on X"},
    )
    assert r.status_code == 200
    return r.json()["id"]


async def test_list_requires_auth(client: AsyncClient):
    course_id, _, _ = await _setup(client)
    r = await client.get(f"/api/v1/courses/{course_id}/forums")
    assert r.status_code == 401


async def test_list_requires_access(client: AsyncClient):
    course_id, _, _ = await _setup(client)
    token, _ = await register_verified_user(client, "fo-outsider@aiacademy.tj")
    r = await client.get(
        f"/api/v1/courses/{course_id}/forums", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "not_purchased"


async def test_create_and_list_with_counts(client: AsyncClient):
    course_id, owner_h, student_h = await _setup(client)
    thread_id = await _create_thread(client, course_id, student_h)

    r = await client.get(f"/api/v1/courses/{course_id}/forums", headers=student_h)
    body = r.json()
    assert body["questions_count"] == 1
    assert body["open_questions_count"] == 1
    assert body["resolved_count"] == 0
    thread = body["forums"][0]
    assert thread["id"] == thread_id
    # student authored it: can update, cannot pin
    assert thread["can"]["update"] is True
    assert thread["can"]["pin"] is False

    # owner sees pin permission
    r = await client.get(f"/api/v1/courses/{course_id}/forums", headers=owner_h)
    assert r.json()["forums"][0]["can"]["pin"] is True


async def test_pin_thread_owner_only(client: AsyncClient):
    course_id, owner_h, student_h = await _setup(client)
    thread_id = await _create_thread(client, course_id, student_h)

    r = await client.post(f"/api/v1/forums/{thread_id}/pin", headers=student_h)
    assert r.status_code == 403

    r = await client.post(f"/api/v1/forums/{thread_id}/pin", headers=owner_h)
    assert r.status_code == 200
    assert r.json()["pin"] is True


async def test_answers_flow_and_resolve(client: AsyncClient):
    course_id, owner_h, student_h = await _setup(client)
    thread_id = await _create_thread(client, course_id, student_h)

    # owner answers
    r = await client.post(
        f"/api/v1/forums/{thread_id}/answers",
        headers=owner_h,
        json={"description": "do it like this"},
    )
    assert r.status_code == 200
    answer_id = r.json()["id"]

    # list answers
    r = await client.get(f"/api/v1/forums/{thread_id}/answers", headers=student_h)
    assert len(r.json()) == 1

    # the question author (student) may resolve
    r = await client.post(f"/api/v1/answers/{answer_id}/resolve", headers=student_h)
    assert r.status_code == 200
    assert r.json()["resolved"] is True

    # thread now counts as resolved
    r = await client.get(f"/api/v1/courses/{course_id}/forums", headers=student_h)
    assert r.json()["resolved_count"] == 1
    assert r.json()["forums"][0]["resolved"] is True
    assert r.json()["forums"][0]["answers_count"] == 1


async def test_pin_answer_owner_only(client: AsyncClient):
    course_id, owner_h, student_h = await _setup(client)
    thread_id = await _create_thread(client, course_id, student_h)
    r = await client.post(
        f"/api/v1/forums/{thread_id}/answers", headers=student_h, json={"description": "me too"}
    )
    answer_id = r.json()["id"]

    r = await client.post(f"/api/v1/answers/{answer_id}/pin", headers=student_h)
    assert r.status_code == 403
    r = await client.post(f"/api/v1/answers/{answer_id}/pin", headers=owner_h)
    assert r.status_code == 200
    assert r.json()["pin"] is True


async def test_update_answer_author_only(client: AsyncClient):
    course_id, owner_h, student_h = await _setup(client)
    thread_id = await _create_thread(client, course_id, student_h)
    r = await client.post(
        f"/api/v1/forums/{thread_id}/answers", headers=owner_h, json={"description": "v1"}
    )
    answer_id = r.json()["id"]

    # student is not the answer author
    r = await client.put(
        f"/api/v1/answers/{answer_id}", headers=student_h, json={"description": "hacked"}
    )
    assert r.status_code == 403

    r = await client.put(
        f"/api/v1/answers/{answer_id}", headers=owner_h, json={"description": "v2"}
    )
    assert r.status_code == 200
    assert r.json()["description"] == "v2"


async def test_update_thread_author_only(client: AsyncClient):
    course_id, owner_h, student_h = await _setup(client)
    thread_id = await _create_thread(client, course_id, student_h)

    # owner is not the thread author
    r = await client.put(
        f"/api/v1/forums/{thread_id}",
        headers=owner_h,
        data={"title": "x", "description": "y"},
    )
    assert r.status_code == 403

    r = await client.put(
        f"/api/v1/forums/{thread_id}",
        headers=student_h,
        data={"title": "edited", "description": "updated body"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "edited"
