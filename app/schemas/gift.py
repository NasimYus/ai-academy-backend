from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field

from app.models.gift import GiftStatus


class GiftItemType(str, Enum):
    course = "course"
    bundle = "bundle"


class GiftCreate(BaseModel):
    item_type: GiftItemType
    item_id: int
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    description: str | None = None


class GiftRead(BaseModel):
    id: int
    item_type: GiftItemType
    item_id: int
    item_title: str | None = None
    name: str
    email: str
    description: str | None
    status: GiftStatus
    viewed: bool
    created_at: datetime


class GiftActionResponse(BaseModel):
    message: str
