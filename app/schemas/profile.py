from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import MeetingType, ThemeColorMode, UserStatus
from app.schemas.validators import StrongPassword


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr | None
    mobile: str | None
    full_name: str | None
    role_name: str
    status: UserStatus
    verified: bool
    avatar: str | None
    cover_img: str | None
    bio: str | None
    headline: str | None
    about: str | None
    address: str | None
    language: str | None
    timezone: str | None
    currency: str | None
    theme_color_mode: ThemeColorMode | None
    newsletter: bool
    public_message: bool
    account_type: str | None
    iban: str | None
    account_id: str | None
    meeting_type: MeetingType
    level_of_training: int | None
    country_id: int | None
    province_id: int | None
    city_id: int | None
    district_id: int | None
    created_at: datetime


class LocationInput(BaseModel):
    latitude: float
    longitude: float


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    language: str | None = None
    email: EmailStr | None = None
    mobile: str | None = None
    newsletter: bool | None = None
    public_message: bool | None = None
    timezone: str | None = None
    password: StrongPassword | None = None
    about: str | None = None
    bio: str | None = Field(default=None, min_length=3, max_length=48)
    address: str | None = None
    account_type: str | None = None
    iban: str | None = None
    account_id: str | None = None
    meeting_type: MeetingType | None = None
    # legacy accepts a subset of {beginner, middle, expert}; stored as a bitmask.
    level_of_training: list[str] | None = None
    location: LocationInput | None = None
    country_id: int | None = None
    province_id: int | None = None
    city_id: int | None = None
    district_id: int | None = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: StrongPassword


class PasswordUpdateResult(BaseModel):
    status: str = "updated"
    token: str  # fresh access token (legacy refreshes the JWT)


class ImagesResult(BaseModel):
    status: str = "updated"
    avatar: str | None = None
    identity_scan: str | None = None
    certificate: str | None = None
