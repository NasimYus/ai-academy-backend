from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserStatus
from app.schemas.validators import StrongPassword


class UserCreate(BaseModel):
    email: EmailStr
    password: StrongPassword
    full_name: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr | None
    mobile: str | None
    full_name: str | None
    role_name: str
    status: UserStatus
    verified: bool
    avatar: str | None
    created_at: datetime


class UserBrief(BaseModel):
    """Public, minimal user card (legacy user->brief subset)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str | None
    role_name: str
    avatar: str | None
    headline: str | None
