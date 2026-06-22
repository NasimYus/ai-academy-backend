from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserStatus


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
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
