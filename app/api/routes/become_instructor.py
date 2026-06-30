from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models.become_instructor import BecomeInstructor, BecomeInstructorStatus
from app.models.role import Role
from app.repositories import become_instructor as repo
from app.repositories import users as users_repo
from app.schemas.become_instructor import (
    BecomeInstructorAdminRead,
    BecomeInstructorCreate,
    BecomeInstructorRead,
    BecomeInstructorUser,
)
from app.schemas.common import error_responses

router = APIRouter(tags=["become-instructor"])


def _read(request: BecomeInstructor) -> BecomeInstructorRead:
    return BecomeInstructorRead(
        id=request.id,
        role=request.role,
        description=request.description,
        occupations=request.occupations or [],
        status=request.status.value,
        created_at=request.created_at,
    )


@router.get(
    "/panel/become-instructor",
    response_model=BecomeInstructorRead | None,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def my_request(current_user: CurrentUser, db: DbSession) -> BecomeInstructorRead | None:
    """The student's current become-instructor request, or null if none."""
    request = await repo.get_for_user(db, current_user.id)
    return _read(request) if request else None


@router.post(
    "/panel/become-instructor",
    response_model=BecomeInstructorRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_409_CONFLICT),
)
async def submit_request(
    payload: BecomeInstructorCreate, current_user: CurrentUser, db: DbSession
) -> BecomeInstructorRead:
    """Submit (or re-submit) a request to become an instructor — students only."""
    if current_user.role_name != Role.USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only students can apply"
        )
    existing = await repo.get_for_user(db, current_user.id)
    if existing is not None and existing.status == BecomeInstructorStatus.accept:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already approved")
    request = await repo.upsert(
        db,
        user_id=current_user.id,
        role=payload.role,
        description=payload.description,
        occupations=payload.occupations,
    )
    return _read(request)


# --- Admin moderation ---


def _admin_read(request: BecomeInstructor) -> BecomeInstructorAdminRead:
    return BecomeInstructorAdminRead(
        **_read(request).model_dump(),
        user=BecomeInstructorUser(
            id=request.user.id, full_name=request.user.full_name, email=request.user.email
        ),
    )


@router.get(
    "/admin/become-instructors",
    response_model=list[BecomeInstructorAdminRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def admin_list(admin: AdminUser, db: DbSession) -> list[BecomeInstructorAdminRead]:
    """All become-instructor requests for moderation (newest first)."""
    return [_admin_read(r) for r in await repo.list_requests(db)]


@router.post(
    "/admin/become-instructors/{request_id}/accept",
    response_model=BecomeInstructorAdminRead,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def admin_accept(
    request_id: int, admin: AdminUser, db: DbSession
) -> BecomeInstructorAdminRead:
    """Approve a request: flip the applicant's role to the requested one."""
    request = await repo.get_by_id(db, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    await users_repo.set_role(db, request.user, request.role)
    await repo.set_status(db, request, BecomeInstructorStatus.accept)
    return _admin_read(request)


@router.post(
    "/admin/become-instructors/{request_id}/reject",
    response_model=BecomeInstructorAdminRead,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def admin_reject(
    request_id: int, admin: AdminUser, db: DbSession
) -> BecomeInstructorAdminRead:
    request = await repo.get_by_id(db, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    await repo.set_status(db, request, BecomeInstructorStatus.reject)
    return _admin_read(request)
