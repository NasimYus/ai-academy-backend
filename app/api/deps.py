from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import ACCESS, decode_token
from app.models.user import User, UserStatus
from app.repositories import users as users_repo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_token(token, expected_purpose=ACCESS)
    if subject is None:
        raise credentials_exc
    user = await users_repo.get_by_id(db, int(subject))
    if user is None or user.status != UserStatus.active:
        raise credentials_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    db: DbSession, authorization: Annotated[str | None, Header()] = None
) -> User | None:
    """Resolve the user from a Bearer token if present; never raises."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    subject = decode_token(authorization[7:], expected_purpose=ACCESS)
    if subject is None:
        return None
    user = await users_repo.get_by_id(db, int(subject))
    if user is None or user.status != UserStatus.active:
        return None
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_role(*role_names: str):
    """Allow only the exact given role names."""

    async def checker(user: CurrentUser) -> User:
        if user.role_name not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return checker


# Hierarchical access map, mirrors legacy Api\LevelAccess middleware.
LEVEL_ACCESS: dict[str, set[str]] = {
    "user": {"user", "teacher", "organization"},
    "teacher": {"organization", "teacher"},
    "organization": {"organization"},
}


def require_level(level: str):
    """Allow roles permitted at the given access level (legacy level-access)."""

    async def checker(user: CurrentUser) -> User:
        if user.role_name not in LEVEL_ACCESS.get(level, set()):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return checker
