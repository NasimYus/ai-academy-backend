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


async def _admin(client: AsyncClient, email: str) -> tuple[str, int]:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.ADMIN
        await db.commit()
    return token, uid


async def test_create_bundle_single_page(client: AsyncClient):
    token, tid = await _teacher(client, email="bundlemaker@aiacademy.tj")
    payload = {
        "title": "Fullstack Pack",
        "locale": "ru",
        "points": 100,
        "price": 500,
        "certificate": True,
        "private": True,
        "subscribe": True,
        "message_for_reviewer": "check",
    }
    r = await client.post("/api/v1/panel/bundles", json=payload, headers=_auth(token))
    assert r.status_code == 201
    bundle_id = r.json()["id"]
    async with AsyncSessionLocal() as db:
        b = await db.get(Bundle, bundle_id)
        assert b.title == "Fullstack Pack"
        assert b.certificate is True and b.private is True and b.subscribe is True
        assert b.points == 100
        assert b.creator_id == tid and b.teacher_id == tid
        assert b.slug  # auto-generated


async def test_admin_creates_bundle_for_instructor(client: AsyncClient):
    _, teacher_id = await _teacher(client, email="bundleteacher@aiacademy.tj")
    admin_token, admin_id = await _admin(client, email="bundleadmin@aiacademy.tj")
    r = await client.post(
        "/api/v1/panel/bundles",
        json={"title": "Admin Pack", "teacher_id": teacher_id},
        headers=_auth(admin_token),
    )
    assert r.status_code == 201
    async with AsyncSessionLocal() as db:
        b = await db.get(Bundle, r.json()["id"])
        assert b.teacher_id == teacher_id
        assert b.creator_id == admin_id


async def test_admin_bundles_list(client: AsyncClient):
    _, tid = await _teacher(client, email="blt@aiacademy.tj")
    c = await _course(tid, "blc")
    await _bundle(tid, [c], slug="admin-list-bundle")
    admin_token, _ = await _admin(client, email="bundlelistadmin@aiacademy.tj")

    # student forbidden
    student_token, _ = await register_verified_user(client, email="bstudent@aiacademy.tj")
    assert (
        await client.get("/api/v1/admin/bundles", headers=_auth(student_token))
    ).status_code == 403

    r = await client.get("/api/v1/admin/bundles", headers=_auth(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    row = next(b for b in body["bundles"] if b["title"] == "My Bundle")
    assert row["webinars_count"] == 1
    assert row["teacher_name"] is not None
