from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import create_token, hash_password, verify_password
from app.models.role import Role
from app.models.user import UserStatus
from app.repositories import users as users_repo
from app.schemas.auth import (
    AuthToken,
    LoginRequest,
    LoginResponse,
    LogoutResult,
    RegisterStep1,
    RegisterStep1Response,
    RegisterStep2,
    RegisterStep3,
    VerificationConfirm,
    VerificationResult,
)
from app.schemas.common import error_responses
from app.schemas.user import UserRead
from app.services import verification as verification_svc

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register/step/1",
    response_model=RegisterStep1Response,
    responses=error_responses(status.HTTP_409_CONFLICT, status.HTTP_422_UNPROCESSABLE_ENTITY),
)
async def register_step_one(payload: RegisterStep1, db: DbSession) -> RegisterStep1Response:
    # Determine the identifier type from what was sent.
    if payload.mobile:
        field = "mobile"
    elif payload.email:
        field = "email"
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="email or mobile is required"
        )

    if settings.register_method != field:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invalid_register_method")

    if payload.password != payload.password_confirmation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="passwords do not match"
        )

    if field == "mobile":
        if not payload.country_code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="country_code is required"
            )
        value = payload.country_code.lstrip("+") + payload.mobile.lstrip("0")
        verification_value = f"+{value}"
    else:
        value = payload.email
        verification_value = payload.email

    existing = await users_repo.get_by_field(db, field, value)
    if existing is not None:
        result = await verification_svc.check_confirmed(
            db, user=existing, field=field, value=verification_value
        )
        existing.password = hash_password(payload.password)
        await db.commit()
        if result["status"] == "verified":
            if existing.full_name:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="already_registered"
                )
            return RegisterStep1Response(status="go_step_3", user_id=existing.id)
        return RegisterStep1Response(status="go_step_2", user_id=existing.id, code=result["code"])

    user = await users_repo.create(
        db,
        email=value if field == "email" else None,
        mobile=value if field == "mobile" else None,
        password=payload.password,
        role_name=Role.USER,
        status=(
            UserStatus.active
            if settings.disable_registration_verification_process
            else UserStatus.pending
        ),
        affiliate=settings.users_affiliate_status,
    )
    # NOTE(Phase 5): custom form fields / certificate meta are skipped until those
    # subsystems are ported (no-op on a clean install, as in legacy).
    result = await verification_svc.check_confirmed(
        db, user=user, field=field, value=verification_value
    )
    return RegisterStep1Response(status="stored", user_id=user.id, code=result["code"])


@router.post(
    "/register/step/2",
    response_model=VerificationResult,
    responses=error_responses(status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY),
)
async def register_step_two(payload: RegisterStep2, db: DbSession) -> VerificationResult:
    user = await users_repo.get_by_id(db, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    value = user.email or user.mobile
    if value is None or not await verification_svc.confirm_code(db, value=value, code=payload.code):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid or expired code"
        )
    return VerificationResult()


@router.post(
    "/register/step/3",
    response_model=AuthToken,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def register_step_three(payload: RegisterStep3, db: DbSession) -> AuthToken:
    user = await users_repo.get_by_id(db, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.full_name = payload.full_name
    # NOTE(Phase 5): registration bonus, reward accounting and referral handling
    # are gated behind their settings (off on a clean install) — ported later.
    await db.commit()
    return AuthToken(access_token=create_token(str(user.id)), user_id=user.id)


@router.post(
    "/verification",
    response_model=VerificationResult,
    responses=error_responses(status.HTTP_422_UNPROCESSABLE_ENTITY),
)
async def verification(payload: VerificationConfirm, db: DbSession) -> VerificationResult:
    if not await verification_svc.confirm_code(db, value=payload.username, code=payload.code):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid or expired code"
        )
    return VerificationResult()


@router.post(
    "/login",
    response_model=LoginResponse,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    field = verification_svc.detect_field(payload.username)
    value = payload.username.lstrip("+") if field == "mobile" else payload.username

    user = await users_repo.get_by_field(db, field, value)
    if user is None or not verify_password(payload.password, user.password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )

    # Ban check, with auto-unban once the ban window has elapsed.
    if user.ban and user.ban_end_at is not None:
        now = datetime.now(timezone.utc)
        if user.ban_end_at > now:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="banned_account")
        user.ban = False
        user.ban_start_at = None
        user.ban_end_at = None
        await db.commit()

    # Inactive accounts trigger a fresh verification code instead of logging in.
    if user.status != UserStatus.active:
        await verification_svc.check_confirmed(
            db,
            user=user,
            field=field,
            value=f"+{value}" if field == "mobile" else value,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_verified")

    # Device limit (legacy security setting; off by default).
    if settings.login_device_limit and user.logged_count >= settings.number_of_allowed_devices:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="limit_account")

    user.logged_count += 1
    # TODO(Phase 5): UserFirebaseSessions row + login-history entry.
    await db.commit()

    profile_completion = [] if user.full_name else ["full_name"]
    return LoginResponse(
        access_token=create_token(str(user.id)),
        user_id=user.id,
        profile_completion=profile_completion,
    )


@router.post(
    "/logout",
    response_model=LogoutResult,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def logout(current_user: CurrentUser, db: DbSession) -> LogoutResult:
    if current_user.logged_count > 0:
        current_user.logged_count -= 1
    # TODO: delete the UserFirebaseSessions row and add the JWT to a denylist
    # once those subsystems land (stateless JWT has no server-side revocation yet).
    await db.commit()
    return LogoutResult()


@router.get(
    "/me",
    response_model=UserRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def me(current_user: CurrentUser) -> UserRead:
    return current_user
