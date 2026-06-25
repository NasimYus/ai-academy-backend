from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user import UserStatus


class AdminUserRead(BaseModel):
    id: int
    full_name: str | None
    email: str | None
    mobile: str | None
    role_name: str
    role_id: int
    status: UserStatus
    ban: bool
    ban_end_at: datetime | None
    created_at: datetime


class AdminUserList(BaseModel):
    count: int
    users: list[AdminUserRead]


class BanRequest(BaseModel):
    # Ban duration in days; null = permanent (far-future end).
    days: int | None = Field(default=None, ge=1)


class RoleRequest(BaseModel):
    role_id: int
