from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.role import Role
from app.models.user import User, UserStatus


async def _seed() -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        teacher = User(
            full_name="Teacher One",
            email="t1@x.tj",
            role_name=Role.TEACHER,
            role_id=4,
            status=UserStatus.active,
        )
        org = User(
            full_name="Org One",
            email="o1@x.tj",
            role_name=Role.ORGANIZATION,
            role_id=3,
            status=UserStatus.active,
        )
        banned = User(
            full_name="Banned Teacher",
            email="b@x.tj",
            role_name=Role.TEACHER,
            role_id=4,
            status=UserStatus.active,
            ban=True,
        )
        student = User(
            full_name="Student",
            email="s@x.tj",
            role_name=Role.USER,
            role_id=1,
            status=UserStatus.active,
        )
        db.add_all([teacher, org, banned, student])
        await db.flush()
        db.add(
            Course(
                title="T1 Course",
                slug="t1c",
                type=CourseType.course,
                status=CourseStatus.active,
                price=0,
                teacher_id=teacher.id,
            )
        )
        await db.commit()
        return {"teacher": teacher.id, "student": student.id}


async def test_instructors_excludes_banned_and_non_teachers(client: AsyncClient):
    await _seed()
    r = await client.get("/api/v1/providers/instructors")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["users"][0]["full_name"] == "Teacher One"


async def test_organizations(client: AsyncClient):
    await _seed()
    r = await client.get("/api/v1/providers/organizations")
    assert [u["full_name"] for u in r.json()["users"]] == ["Org One"]


async def test_consultations_empty(client: AsyncClient):
    await _seed()
    r = await client.get("/api/v1/providers/consultations")
    assert r.json() == {"count": 0, "users": []}


async def test_public_profile_with_courses(client: AsyncClient):
    ids = await _seed()
    r = await client.get(f"/api/v1/users/{ids['teacher']}/profile")
    assert r.status_code == 200
    body = r.json()
    assert body["full_name"] == "Teacher One"
    assert body["courses_count"] == 1
    assert body["courses"][0]["slug"] == "t1c"


async def test_public_profile_404(client: AsyncClient):
    r = await client.get("/api/v1/users/99999/profile")
    assert r.status_code == 404
