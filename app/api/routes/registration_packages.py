from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, require_level
from app.models.registration_package import RegistrationPackage
from app.models.user import User
from app.repositories import registration_packages as packages_repo
from app.schemas.common import error_responses
from app.schemas.registration_package import (
    PackageList,
    PackageResponse,
    RegistrationPackageRead,
)
from app.services import registration_packages as packages_service

router = APIRouter(prefix="/registration-packages", tags=["registration-packages"])

TeacherUser = Annotated[User, Depends(require_level("teacher"))]


def _read(plan: RegistrationPackage, *, is_active: bool) -> RegistrationPackageRead:
    return RegistrationPackageRead(
        id=plan.id,
        role=plan.role,
        title=plan.title,
        description=plan.description,
        icon=plan.icon,
        days=plan.days,
        price=float(plan.price),
        instructors_count=plan.instructors_count,
        students_count=plan.students_count,
        courses_capacity=plan.courses_capacity,
        courses_count=plan.courses_count,
        meeting_count=plan.meeting_count,
        status=plan.status,
        is_active=is_active,
    )


@router.get("", response_model=PackageList)
async def list_packages(current_user: TeacherUser, db: DbSession) -> PackageList:
    """Packages for the instructor's role + their active package (legacy index)."""
    role = packages_service.role_for(current_user)
    plans = await packages_repo.list_active_for_role(db, role)
    active = await packages_service.active_package(db, current_user.id)
    active_id = active.package_id if active else None
    return PackageList(
        packages=[_read(p, is_active=(p.id == active_id)) for p in plans],
        active_package=active,
    )


@router.post(
    "/{package_id}/activate",
    response_model=PackageResponse,
    responses=error_responses(status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def activate_package(
    package_id: int, current_user: TeacherUser, db: DbSession
) -> PackageResponse:
    """Activate a free package (paid checkout via the order flow is deferred)."""
    plan = await packages_repo.get_plan(db, package_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    if plan.role != packages_service.role_for(current_user):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="wrong_role")
    if float(plan.price) > 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_free")
    await packages_repo.create_user_package(db, user_id=current_user.id, package_id=plan.id)
    return PackageResponse(message="activated")
