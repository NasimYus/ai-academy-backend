"""Registration packages — parity of RegistrationPackagesController + UserPackage.

The active package is the user's latest activation that is still within its
`days` window (null `days` = unlimited / never expires). Quota enforcement
(courses/meetings caps) is deferred.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.registration_package import PackageRole
from app.models.user import User
from app.repositories import registration_packages as packages_repo
from app.schemas.registration_package import ActivePackage


def role_for(user: User) -> PackageRole:
    return (
        PackageRole.organizations if user.role_name == "organization" else PackageRole.instructors
    )


async def active_package(db: AsyncSession, user_id: int) -> ActivePackage | None:
    latest = await packages_repo.latest_user_package(db, user_id)
    if latest is None:
        return None
    plan = latest.package
    days_remained: int | None = None
    if plan.days is not None:
        elapsed = (datetime.now(UTC) - latest.created_at).days
        if elapsed > plan.days:
            return None  # expired
        days_remained = plan.days - elapsed
    return ActivePackage(
        package_id=plan.id,
        title=plan.title,
        activation_date=latest.created_at,
        days_remained=days_remained,
        instructors_count=plan.instructors_count,
        students_count=plan.students_count,
        courses_capacity=plan.courses_capacity,
        courses_count=plan.courses_count,
        meeting_count=plan.meeting_count,
    )
