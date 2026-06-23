from datetime import datetime

from pydantic import BaseModel


class ContentItem(BaseModel):
    """A lesson item (file / text_lesson / session). Gated payload fields are
    null when `locked` (user lacks access and the item isn't free)."""

    id: int
    type: str  # "file" | "text_lesson" | "session"
    title: str
    accessibility: str
    order: int
    locked: bool

    # file
    file: str | None = None
    file_type: str | None = None
    volume: str | None = None
    # text_lesson
    image: str | None = None
    study_time: int | None = None
    summary: str | None = None
    content: str | None = None
    # session
    link: str | None = None
    session_date: datetime | None = None
    duration: int | None = None
    description: str | None = None


class ChapterRead(BaseModel):
    id: int
    title: str
    order: int
    items: list[ContentItem] = []


class CourseContent(BaseModel):
    chapters: list[ChapterRead] = []
    items: list[ContentItem] = []  # top-level (no chapter)
    has_access: bool = False
