from datetime import datetime

from pydantic import BaseModel, Field


class ChapterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChapterUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChapterReorder(BaseModel):
    ordered_ids: list[int]


class ChapterManage(BaseModel):
    """Instructor content-editor row (legacy chapter card)."""

    id: int
    title: str
    order: int
    items_count: int = 0
    duration: int = 0  # minutes


class CourseContentManage(BaseModel):
    course_id: int
    chapters: list[ChapterManage] = []


class ContentItem(BaseModel):
    """A lesson item (file / text_lesson / session). Gated payload fields are
    null when `locked` (user lacks access and the item isn't free)."""

    id: int
    type: str  # "file" | "text_lesson" | "session"
    title: str
    accessibility: str
    order: int
    locked: bool
    completed: bool = False

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
    course_id: int
    chapters: list[ChapterRead] = []
    items: list[ContentItem] = []  # top-level (no chapter)
    has_access: bool = False
