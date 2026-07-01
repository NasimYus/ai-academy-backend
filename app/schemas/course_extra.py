from pydantic import BaseModel, Field

from app.models.course_extra import ExtraType


class FaqInput(BaseModel):
    question: str = Field(min_length=1, max_length=512)
    answer: str | None = None
    locale: str = "ru"


class FaqRead(BaseModel):
    id: int
    question: str
    answer: str | None = None
    locale: str


class ExtraInput(BaseModel):
    type: ExtraType
    title: str = Field(min_length=1, max_length=512)
    locale: str = "ru"


class ExtraRead(BaseModel):
    id: int
    type: ExtraType
    title: str
    locale: str


class LogoInput(BaseModel):
    image: str


class LogoRead(BaseModel):
    id: int
    image: str
