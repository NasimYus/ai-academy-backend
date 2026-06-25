from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AdminUser, DbSession
from app.models.role import Role
from app.models.user import User, UserStatus
from app.repositories import users as users_repo
from app.schemas.admin_user import AdminUserList, AdminUserRead, BanRequest, RoleRequest
from app.schemas.common import error_responses

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

_ADMIN_ERRORS = error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
_NOT_FOUND = error_responses(
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN,
    status.HTTP_404_NOT_FOUND,
    status.HTTP_422_UNPROCESSABLE_CONTENT,
)

_PERMANENT_DAYS = 36500  # ~100 years stands in for a permanent ban


def _read(user: User) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        mobile=user.mobile,
        role_name=user.role_name,
        role_id=user.role_id,
        status=user.status,
        ban=user.ban,
        ban_end_at=user.ban_end_at,
        created_at=user.created_at,
    )


@router.get("", response_model=AdminUserList, responses=_ADMIN_ERRORS)
async def list_users(
    admin: AdminUser,
    db: DbSession,
    role: Annotated[str | None, Query()] = None,
    status_filter: Annotated[UserStatus | None, Query(alias="status")] = None,
    banned: Annotated[bool | None, Query()] = None,
) -> AdminUserList:
    """Users for admin management, newest first (filters: role/status/banned)."""
    users = await users_repo.admin_list(db, role_name=role, status=status_filter, banned=banned)
    return AdminUserList(count=len(users), users=[_read(u) for u in users])


async def _get_target(db: DbSession, admin: User, user_id: int) -> User:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="cannot_modify_self"
        )
    user = await users_repo.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/{user_id}/ban", response_model=AdminUserRead, responses=_NOT_FOUND)
async def ban_user(
    user_id: int, payload: BanRequest, admin: AdminUser, db: DbSession
) -> AdminUserRead:
    """Ban a user for `days` (or permanently). Login is blocked until ban_end_at."""
    user = await _get_target(db, admin, user_id)
    now = datetime.now(UTC)
    user.ban = True
    user.ban_start_at = now
    user.ban_end_at = now + timedelta(days=payload.days or _PERMANENT_DAYS)
    await db.commit()
    return _read(user)


@router.post("/{user_id}/unban", response_model=AdminUserRead, responses=_NOT_FOUND)
async def unban_user(user_id: int, admin: AdminUser, db: DbSession) -> AdminUserRead:
    """Lift a ban (clears the ban window)."""
    user = await _get_target(db, admin, user_id)
    user.ban = False
    user.ban_start_at = None
    user.ban_end_at = None
    await db.commit()
    return _read(user)


@router.post("/{user_id}/role", response_model=AdminUserRead, responses=_NOT_FOUND)
async def set_role(
    user_id: int, payload: RoleRequest, admin: AdminUser, db: DbSession
) -> AdminUserRead:
    """Change a user's role (legacy admin user update → role_id + role_name)."""
    user = await _get_target(db, admin, user_id)
    role = await db.get(Role, payload.role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="bad_role")
    user.role_id = role.id
    user.role_name = role.name
    await db.commit()
    return _read(user)
