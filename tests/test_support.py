from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.support import SupportDepartment
from tests.conftest import register_verified_user


async def _seed_department(title: str = "Billing") -> int:
    async with AsyncSessionLocal() as db:
        d = SupportDepartment(title=title)
        db.add(d)
        await db.commit()
        return d.id


async def _seed_course(slug: str, teacher_id: int | None = None) -> int:
    async with AsyncSessionLocal() as db:
        c = Course(
            title="Course",
            slug=slug,
            type=CourseType.course,
            status=CourseStatus.active,
            price=10,
            teacher_id=teacher_id,
        )
        db.add(c)
        await db.commit()
        return c.id


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_departments_listed(client: AsyncClient):
    await _seed_department("Billing")
    r = await client.get("/api/v1/support/departments")
    assert r.status_code == 200
    assert [d["title"] for d in r.json()] == ["Billing"]


async def test_create_platform_ticket(client: AsyncClient):
    token, _ = await register_verified_user(client)
    dept = await _seed_department()
    r = await client.post(
        "/api/v1/support",
        headers=_auth(token),
        data={
            "title": "Need help",
            "type": "platform_support",
            "department_id": str(dept),
            "message": "My payment failed",
        },
    )
    assert r.status_code == 200

    idx = (await client.get("/api/v1/support", headers=_auth(token))).json()
    assert len(idx["tickets"]) == 1
    ticket = idx["tickets"][0]
    assert ticket["type"] == "platform_support"
    assert ticket["department"] == "Billing"
    assert ticket["status"] == "open"
    assert ticket["conversations"][0]["message"] == "My payment failed"
    assert ticket["conversations"][0]["sender"]["full_name"] == "Test User"
    assert idx["class_support"] == []


async def test_create_course_ticket_in_class_support(client: AsyncClient):
    token, _ = await register_verified_user(client)
    course_id = await _seed_course("c-sup")
    r = await client.post(
        "/api/v1/support",
        headers=_auth(token),
        data={
            "title": "Lesson broken",
            "type": "course_support",
            "course_id": str(course_id),
            "message": "Video does not load",
        },
    )
    assert r.status_code == 200

    rows = (await client.get("/api/v1/support/class_support", headers=_auth(token))).json()
    assert len(rows) == 1
    assert rows[0]["type"] == "course_support"
    assert rows[0]["course"]["id"] == course_id


async def test_store_validation(client: AsyncClient):
    token, _ = await register_verified_user(client)
    base = {"title": "Title", "message": "Message body"}
    # course_support without course_id
    r = await client.post(
        "/api/v1/support",
        headers=_auth(token),
        data={**base, "type": "course_support"},
    )
    assert r.status_code == 400
    # platform_support without department_id
    r = await client.post(
        "/api/v1/support",
        headers=_auth(token),
        data={**base, "type": "platform_support"},
    )
    assert r.status_code == 400
    # unknown department
    r = await client.post(
        "/api/v1/support",
        headers=_auth(token),
        data={**base, "type": "platform_support", "department_id": "9999"},
    )
    assert r.status_code == 404


async def test_teacher_sees_my_class_support(client: AsyncClient):
    teacher_token, teacher_id = await register_verified_user(client, email="teacher@aiacademy.tj")
    student_token, _ = await register_verified_user(client, email="student@aiacademy.tj")
    course_id = await _seed_course("taught", teacher_id=teacher_id)

    await client.post(
        "/api/v1/support",
        headers=_auth(student_token),
        data={
            "title": "Help",
            "type": "course_support",
            "course_id": str(course_id),
            "message": "Question about lesson 3",
        },
    )

    teacher_idx = (await client.get("/api/v1/support", headers=_auth(teacher_token))).json()
    assert len(teacher_idx["my_class_support"]) == 1
    assert teacher_idx["class_support"] == []  # the teacher didn't open it
    assert teacher_idx["my_class_support"][0]["course"]["id"] == course_id


async def test_reply_and_close(client: AsyncClient):
    token, _ = await register_verified_user(client)
    dept = await _seed_department()
    await client.post(
        "/api/v1/support",
        headers=_auth(token),
        data={
            "title": "Hi",
            "type": "platform_support",
            "department_id": str(dept),
            "message": "first",
        },
    )
    support_id = (await client.get("/api/v1/support", headers=_auth(token))).json()["tickets"][0][
        "id"
    ]

    r = await client.post(
        f"/api/v1/support/{support_id}/conversations",
        headers=_auth(token),
        data={"message": "second message"},
    )
    assert r.status_code == 200

    detail = (await client.get(f"/api/v1/support/{support_id}", headers=_auth(token))).json()
    assert [c["message"] for c in detail["conversations"]] == ["first", "second message"]
    assert detail["status"] == "open"  # owner reply keeps it open

    r = await client.get(f"/api/v1/support/{support_id}/close", headers=_auth(token))
    assert r.status_code == 200
    detail = (await client.get(f"/api/v1/support/{support_id}", headers=_auth(token))).json()
    assert detail["status"] == "close"


async def test_reply_to_foreign_ticket_404(client: AsyncClient):
    owner_token, _ = await register_verified_user(client, email="owner@aiacademy.tj")
    other_token, _ = await register_verified_user(client, email="other@aiacademy.tj")
    dept = await _seed_department()
    await client.post(
        "/api/v1/support",
        headers=_auth(owner_token),
        data={
            "title": "Hi",
            "type": "platform_support",
            "department_id": str(dept),
            "message": "owner message",
        },
    )
    support_id = (await client.get("/api/v1/support", headers=_auth(owner_token))).json()[
        "tickets"
    ][0]["id"]

    r = await client.post(
        f"/api/v1/support/{support_id}/conversations",
        headers=_auth(other_token),
        data={"message": "intruder message"},
    )
    assert r.status_code == 404


async def test_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/support")).status_code == 401
