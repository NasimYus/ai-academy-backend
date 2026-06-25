from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.registration_package import (
    PackageRole,
    PackageStatus,
    RegistrationPackage,
)
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


async def _seed_package(
    *,
    price: float = 0,
    role: PackageRole = PackageRole.instructors,
    status: PackageStatus = PackageStatus.active,
    days: int | None = 30,
    title: str = "Starter",
) -> int:
    async with AsyncSessionLocal() as db:
        pkg = RegistrationPackage(
            role=role,
            title=title,
            price=price,
            days=days,
            courses_count=10,
            status=status,
        )
        db.add(pkg)
        await db.commit()
        return pkg.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_list_requires_teacher(client: AsyncClient):
    token, _ = await register_verified_user(client, email="plain@aiacademy.tj")
    r = await client.get("/api/v1/registration-packages", headers=_auth(token))
    assert r.status_code == 403


async def test_list_for_role_and_activate(client: AsyncClient):
    token, _ = await _teacher(client)
    pkg_id = await _seed_package(title="Starter")
    # an organizations package must not appear for a teacher
    await _seed_package(role=PackageRole.organizations, title="Org")
    # a disabled package must not appear
    await _seed_package(status=PackageStatus.disabled, title="Off")

    listed = await client.get("/api/v1/registration-packages", headers=_auth(token))
    assert listed.status_code == 200
    body = listed.json()
    assert [p["title"] for p in body["packages"]] == ["Starter"]
    assert body["active_package"] is None

    act = await client.post(
        f"/api/v1/registration-packages/{pkg_id}/activate", headers=_auth(token)
    )
    assert act.status_code == 200
    assert act.json()["message"] == "activated"

    after = await client.get("/api/v1/registration-packages", headers=_auth(token))
    assert after.json()["active_package"]["package_id"] == pkg_id
    assert after.json()["active_package"]["days_remained"] == 30
    assert after.json()["packages"][0]["is_active"] is True


async def test_activate_paid_rejected(client: AsyncClient):
    token, _ = await _teacher(client)
    pkg_id = await _seed_package(price=50)
    r = await client.post(f"/api/v1/registration-packages/{pkg_id}/activate", headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "not_free"


async def test_activate_wrong_role_rejected(client: AsyncClient):
    token, _ = await _teacher(client)
    pkg_id = await _seed_package(role=PackageRole.organizations)
    r = await client.post(f"/api/v1/registration-packages/{pkg_id}/activate", headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "wrong_role"
