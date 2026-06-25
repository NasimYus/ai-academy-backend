from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.comment import Comment
from app.models.course import Course, CourseStatus, CourseType
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _teacher(client: AsyncClient, email: str = "teacher@aiacademy.tj") -> tuple[str, int]:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return token, uid


async def _course(teacher_id: int, slug: str = "c1") -> int:
    async with AsyncSessionLocal() as db:
        c = Course(
            title="Course",
            slug=slug,
            type=CourseType.course,
            status=CourseStatus.active,
            price=10,
            teacher_id=teacher_id,
            creator_id=teacher_id,
        )
        db.add(c)
        await db.commit()
        return c.id


async def _comment(course_id: int, user_id: int, text: str = "Great course") -> int:
    async with AsyncSessionLocal() as db:
        c = Comment(course_id=course_id, user_id=user_id, comment=text)
        db.add(c)
        await db.commit()
        return c.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_my_class_comments(client: AsyncClient):
    token, tid = await _teacher(client)
    _, student = await register_verified_user(client, email="stu@aiacademy.tj")
    course_id = await _course(tid)
    # a comment on my course + a comment on someone else's course
    await _comment(course_id, student)
    _, other = await _teacher(client, email="other@aiacademy.tj")
    foreign_course = await _course(other, slug="oc")
    await _comment(foreign_course, student, text="not mine")

    r = await client.get("/api/v1/panel/comments", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["comment"] == "Great course"


async def test_reply_threaded(client: AsyncClient):
    token, tid = await _teacher(client)
    _, student = await register_verified_user(client, email="stu@aiacademy.tj")
    course_id = await _course(tid)
    parent = await _comment(course_id, student)

    r = await client.post(
        f"/api/v1/panel/comments/{parent}/reply",
        json={"reply": "Thanks for the feedback!"},
        headers=_auth(token),
    )
    assert r.status_code == 200

    tree = (await client.get("/api/v1/panel/comments", headers=_auth(token))).json()
    assert len(tree) == 1  # reply nests under the parent, not a second root
    assert tree[0]["replies"][0]["comment"] == "Thanks for the feedback!"


async def test_reply_foreign_comment_404(client: AsyncClient):
    token, tid = await _teacher(client)
    other_token, other = await _teacher(client, email="other@aiacademy.tj")
    _, student = await register_verified_user(client, email="stu@aiacademy.tj")
    foreign_course = await _course(other, slug="oc")
    parent = await _comment(foreign_course, student)

    r = await client.post(
        f"/api/v1/panel/comments/{parent}/reply",
        json={"reply": "intruding"},
        headers=_auth(token),
    )
    assert r.status_code == 404


async def test_requires_teacher(client: AsyncClient):
    token, _ = await register_verified_user(client)
    assert (await client.get("/api/v1/panel/comments", headers=_auth(token))).status_code == 403
