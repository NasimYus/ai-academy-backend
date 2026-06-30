from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class BecomeInstructorCreate(BaseModel):
    role: Literal["teacher", "organization"] = "teacher"
    occupations: list[int] = []
    description: str | None = None


class BecomeInstructorRead(BaseModel):
    id: int
    role: str
    description: str | None = None
    occupations: list[int] = []
    status: str  # pending | accept | reject
    created_at: datetime


class BecomeInstructorUser(BaseModel):
    id: int
    full_name: str | None = None
    email: str | None = None


class BecomeInstructorAdminRead(BecomeInstructorRead):
    user: BecomeInstructorUser
