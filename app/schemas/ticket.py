from datetime import datetime

from pydantic import BaseModel, Field


class TicketInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    discount: float = Field(default=0, ge=0, le=100)
    capacity: int | None = Field(default=None, ge=0)
    start_date: datetime | None = None
    end_date: datetime | None = None


class TicketRead(BaseModel):
    id: int
    title: str
    discount: float
    capacity: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
