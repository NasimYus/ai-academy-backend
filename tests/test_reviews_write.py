from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus, CourseType
from app.models.enrollment import Enrollment, EnrollmentSource
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _course(slug: str, course_status: CourseStatus = CourseStatus.active) -> int:
    async with AsyncSessionLocal() as db:
        c = Course(title=slug, slug=slug, type=CourseType.course, status=course_status, price=10)
        db.add(c)
        await db.commit()
        await db.refresh(c)
        return c.id


async def _enroll(user_id: int, course_id: int) -> None:
    async with AsyncSessionLocal() as db:
        db.add(Enrollment(user_id=user_id, course_id=course_id, source=EnrollmentSource.purchase))
        await db.commit()


async def _admin(client: AsyncClient, email: str = "revadmin@aiacademy.tj") -> str:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.ADMIN
        user.role_id = 2
        await db.commit()
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _slug(course_id: int) -> str:
    async with AsyncSessionLocal() as db:
        course = await db.get(Course, course_id)
        return course.slug


_RATING = {
    "content_quality": 5,
    "instructor_skills": 4,
    "purchase_worth": 5,
    "support_quality": 4,
    "description": "Отличный курс",
}


async def test_enrolled_user_can_review(client: AsyncClient):
    token, uid = await register_verified_user(client, email="reviewer@aiacademy.tj")
    course_id = await _course("rev-course")
    await _enroll(uid, course_id)

    r = await client.post(
        f"/api/v1/courses/{course_id}/reviews", headers=_auth(token), json=_RATING
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rates"] == 18  # 5+4+5+4
    assert body["description"] == "Отличный курс"


async def test_review_pending_hidden_until_approved(client: AsyncClient):
    token, uid = await register_verified_user(client, email="rev2@aiacademy.tj")
    course_id = await _course("rev-course2")
    await _enroll(uid, course_id)
    await client.post(f"/api/v1/courses/{course_id}/reviews", headers=_auth(token), json=_RATING)

    detail = (await client.get(f"/api/v1/courses/{await _slug(course_id)}")).json()
    assert detail["reviews_count"] == 0
    assert detail["reviews"] == []


async def test_cannot_review_without_access(client: AsyncClient):
    token, _ = await register_verified_user(client, email="rev3@aiacademy.tj")
    course_id = await _course("rev-course3")
    r = await client.post(
        f"/api/v1/courses/{course_id}/reviews", headers=_auth(token), json=_RATING
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "not_bought"


async def test_duplicate_review_rejected(client: AsyncClient):
    token, uid = await register_verified_user(client, email="rev4@aiacademy.tj")
    course_id = await _course("rev-course4")
    await _enroll(uid, course_id)
    await client.post(f"/api/v1/courses/{course_id}/reviews", headers=_auth(token), json=_RATING)

    again = await client.post(
        f"/api/v1/courses/{course_id}/reviews", headers=_auth(token), json=_RATING
    )
    assert again.status_code == 422
    assert again.json()["detail"] == "duplicate_review"


async def test_review_missing_course_404(client: AsyncClient):
    token, _ = await register_verified_user(client, email="rev5@aiacademy.tj")
    r = await client.post("/api/v1/courses/9999/reviews", headers=_auth(token), json=_RATING)
    assert r.status_code == 404


async def test_admin_moderation_approve_then_visible(client: AsyncClient):
    admin_token = await _admin(client)
    token, uid = await register_verified_user(client, email="rev6@aiacademy.tj")
    course_id = await _course("rev-course6")
    await _enroll(uid, course_id)
    review_id = (
        await client.post(
            f"/api/v1/courses/{course_id}/reviews", headers=_auth(token), json=_RATING
        )
    ).json()["id"]

    queue = (await client.get("/api/v1/admin/reviews", headers=_auth(admin_token))).json()
    assert any(r["id"] == review_id for r in queue["reviews"])

    approved = await client.post(
        f"/api/v1/admin/reviews/{review_id}/approve", headers=_auth(admin_token)
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "active"

    detail = (await client.get(f"/api/v1/courses/{await _slug(course_id)}")).json()
    assert detail["reviews_count"] == 1


async def test_admin_reject_deletes(client: AsyncClient):
    admin_token = await _admin(client, email="revadmin2@aiacademy.tj")
    token, uid = await register_verified_user(client, email="rev7@aiacademy.tj")
    course_id = await _course("rev-course7")
    await _enroll(uid, course_id)
    review_id = (
        await client.post(
            f"/api/v1/courses/{course_id}/reviews", headers=_auth(token), json=_RATING
        )
    ).json()["id"]

    rejected = await client.delete(f"/api/v1/admin/reviews/{review_id}", headers=_auth(admin_token))
    assert rejected.status_code == 204
    queue = (await client.get("/api/v1/admin/reviews", headers=_auth(admin_token))).json()
    assert all(r["id"] != review_id for r in queue["reviews"])


async def test_admin_reviews_requires_admin(client: AsyncClient):
    token, _ = await register_verified_user(client, email="rev8@aiacademy.tj")
    r = await client.get("/api/v1/admin/reviews", headers=_auth(token))
    assert r.status_code == 403
