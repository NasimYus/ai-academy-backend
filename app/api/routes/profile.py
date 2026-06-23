from fastapi import APIRouter, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_token, hash_password, verify_password
from app.repositories import users as users_repo
from app.schemas.common import error_responses
from app.schemas.profile import (
    ImagesResult,
    PasswordUpdate,
    PasswordUpdateResult,
    ProfileRead,
    ProfileUpdate,
)
from app.services import storage

router = APIRouter(prefix="/panel/profile-setting", tags=["profile"])

# Legacy levels are a bitmask (UserLevelOfTraining): beginner=1, middle=2, expert=4.
_LEVELS = {"beginner": 1, "middle": 2, "expert": 4}


@router.get("", response_model=ProfileRead, responses=error_responses(status.HTTP_401_UNAUTHORIZED))
async def get_profile(current_user: CurrentUser) -> ProfileRead:
    return current_user


@router.put(
    "",
    response_model=ProfileRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_409_CONFLICT),
)
async def update_profile(payload: ProfileUpdate, current_user: CurrentUser, db: DbSession) -> ProfileRead:
    data = payload.model_dump(exclude_unset=True)

    # Uniqueness checks (excluding self), mirroring the legacy unique rules.
    if "email" in data and data["email"]:
        other = await users_repo.get_by_email(db, data["email"])
        if other is not None and other.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already in use")
    if "mobile" in data and data["mobile"]:
        other = await users_repo.get_by_mobile(db, data["mobile"])
        if other is not None and other.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="mobile already in use")

    if "password" in data:
        current_user.password = hash_password(data.pop("password"))
    if "level_of_training" in data:
        levels = data.pop("level_of_training") or []
        current_user.level_of_training = sum(_LEVELS.get(lvl, 0) for lvl in levels) or None
    if "location" in data:
        loc = data.pop("location")
        current_user.location = f"{loc['latitude']},{loc['longitude']}" if loc else None

    for field, value in data.items():
        setattr(current_user, field, value)

    # NOTE(Phase 5): Newsletter table + reward, UserMeta (gender/age), and Zoom
    # API are gated stubs here — only the users.* columns are updated for now.
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put(
    "/password",
    response_model=PasswordUpdateResult,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def update_password(
    payload: PasswordUpdate, current_user: CurrentUser, db: DbSession
) -> PasswordUpdateResult:
    if not verify_password(payload.current_password, current_user.password or ""):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="incorrect")
    current_user.password = hash_password(payload.new_password)
    await db.commit()
    # Legacy refreshes the JWT after a password change.
    return PasswordUpdateResult(token=create_token(str(current_user.id)))


@router.post(
    "/images",
    response_model=ImagesResult,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def update_images(
    current_user: CurrentUser,
    db: DbSession,
    profile_image: UploadFile | None = None,
    identity_scan: UploadFile | None = None,
    certificate: UploadFile | None = None,
) -> ImagesResult:
    base = f"{current_user.id}"
    if profile_image is not None:
        current_user.avatar = storage.save_upload(profile_image, f"{base}/avatar")
    if identity_scan is not None:
        current_user.identity_scan = storage.save_upload(identity_scan, f"{base}/identity")
    if certificate is not None:
        current_user.certificate = storage.save_upload(certificate, f"{base}/certificate")
    await db.commit()
    return ImagesResult(
        avatar=current_user.avatar,
        identity_scan=current_user.identity_scan,
        certificate=current_user.certificate,
    )
