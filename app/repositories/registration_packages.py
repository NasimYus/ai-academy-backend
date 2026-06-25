from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.registration_package import (
    PackageRole,
    PackageStatus,
    RegistrationPackage,
    UserRegistrationPackage,
)


async def list_active_for_role(db: AsyncSession, role: PackageRole) -> list[RegistrationPackage]:
    result = await db.execute(
        select(RegistrationPackage)
        .where(
            RegistrationPackage.role == role,
            RegistrationPackage.status == PackageStatus.active,
        )
        .order_by(RegistrationPackage.price.asc())
    )
    return list(result.scalars().all())


async def get_plan(db: AsyncSession, package_id: int) -> RegistrationPackage | None:
    return await db.get(RegistrationPackage, package_id)


async def latest_user_package(db: AsyncSession, user_id: int) -> UserRegistrationPackage | None:
    result = await db.execute(
        select(UserRegistrationPackage)
        .where(UserRegistrationPackage.user_id == user_id)
        .options(selectinload(UserRegistrationPackage.package))
        .order_by(UserRegistrationPackage.created_at.desc())
    )
    return result.scalars().first()


async def create_user_package(
    db: AsyncSession, *, user_id: int, package_id: int
) -> UserRegistrationPackage:
    row = UserRegistrationPackage(user_id=user_id, package_id=package_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
