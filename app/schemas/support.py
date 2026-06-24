from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.models.support import SupportStatus
from app.schemas.user import UserBrief


class SupportType(str, Enum):
    course_support = "course_support"
    platform_support = "platform_support"


class SupportCourseRef(BaseModel):
    id: int
    title: str
    slug: str
    image: str | None


class SupportConversationRead(BaseModel):
    message: str
    sender: UserBrief | None
    supporter: UserBrief | None
    attach: str | None
    created_at: datetime


class SupportDetail(BaseModel):
    id: int
    department: str | None
    status: SupportStatus
    type: SupportType
    title: str
    course: SupportCourseRef | None
    user: UserBrief
    conversations: list[SupportConversationRead]
    created_at: datetime
    updated_at: datetime


class SupportIndex(BaseModel):
    class_support: list[SupportDetail]
    my_class_support: list[SupportDetail]
    tickets: list[SupportDetail]


class SupportDepartmentRead(BaseModel):
    id: int
    title: str


class StoredAttach(BaseModel):
    attach: str | None
