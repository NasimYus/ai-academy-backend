from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import (
    VERIFY_EMAIL,
    create_token,
    decode_token,
    verify_password,
)
from app.repositories import users as users_repo
from app.schemas.auth import LoginRequest, RegisterResponse, Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DbSession) -> RegisterResponse:
    existing = await users_repo.get_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await users_repo.create(
        db, email=payload.email, password=payload.password, full_name=payload.full_name
    )
    # TODO: send this token by e-mail. Surfaced in the response for dev only.
    token = create_token(str(user.id), purpose=VERIFY_EMAIL, expires_minutes=60 * 24)
    return RegisterResponse(user_id=user.id, verification_token=token)


@router.post("/verify")
async def verify_email(token: str, db: DbSession) -> dict[str, str]:
    subject = decode_token(token, expected_purpose=VERIFY_EMAIL)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
        )
    user = await users_repo.get_by_id(db, int(subject))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await users_repo.set_verified(db, user)
    return {"detail": "Email verified"}


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: DbSession) -> Token:
    user = await users_repo.get_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return Token(access_token=create_token(str(user.id)))


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return current_user
