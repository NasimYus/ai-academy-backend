from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.bundle import Bundle, BundleStatus, BundleWebinar
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


async def _course(teacher_id: int, slug: str, duration: int = 60) -> int:
    async with AsyncSessionLocal() as db:
        c = Course(
            title="Course",
            slug=slug,
            type=CourseType.course,
            status=CourseStatus.active,
            price=10,
            duration=duration,
            teacher_id=teacher_id,
            creator_id=teacher_id,
        )
        db.add(c)
        await db.commit()
        return c.id


async def _bundle(creator_id: int, course_ids: list[int], slug: str = "b1") -> int:
    async with AsyncSessionLocal() as db:
        b = Bundle(
            creator_id=creator_id,
            teacher_id=creator_id,
            title="My Bundle",
            slug=slug,
            price=100,
            status=BundleStatus.active,
        )
        db.add(b)
        await db.flush()
        for cid in course_ids:
            db.add(BundleWebinar(bundle_id=b.id, course_id=cid, creator_id=creator_id))
        await db.commit()
        return b.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_list_bundles_with_hours(client: AsyncClient):
    token, tid = await _teacher(client)
    c1 = await _course(tid, "c1", duration=60)
    c2 = await _course(tid, "c2", duration=90)
    await _bundle(tid, [c1, c2])

    r = await client.get("/api/v1/panel/bundles", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["bundles_count"] == 1
    assert body["bundles_hours"] == 150
    assert body["bundle_sales_count"] == 0
    assert body["bundles"][0]["webinars_count"] == 2
    assert body["bundles"][0]["title"] == "My Bundle"


async def test_only_own_bundles(client: AsyncClient):
    token, tid = await _teacher(client)
    _, other = await _teacher(client, email="other@aiacademy.tj")
    oc = await _course(other, "oc")
    await _bundle(other, [oc], slug="ob")

    r = await client.get("/api/v1/panel/bundles", headers=_auth(token))
    assert r.json()["bundles_count"] == 0


async def test_delete_bundle(client: AsyncClient):
    token, tid = await _teacher(client)
    c1 = await _course(tid, "c1")
    b_id = await _bundle(tid, [c1])

    r = await client.delete(f"/api/v1/panel/bundles/{b_id}", headers=_auth(token))
    assert r.status_code == 204
    assert (
        await client.delete(f"/api/v1/panel/bundles/{b_id}", headers=_auth(token))
    ).status_code == 404


async def test_delete_foreign_bundle_404(client: AsyncClient):
    token, _ = await _teacher(client)
    _, other = await _teacher(client, email="other@aiacademy.tj")
    oc = await _course(other, "oc")
    b_id = await _bundle(other, [oc], slug="ob")
    assert (
        await client.delete(f"/api/v1/panel/bundles/{b_id}", headers=_auth(token))
    ).status_code == 404


async def test_requires_teacher(client: AsyncClient):
    token, _ = await register_verified_user(client)
    assert (await client.get("/api/v1/panel/bundles", headers=_auth(token))).status_code == 403
