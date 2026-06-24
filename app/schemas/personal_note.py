from datetime import datetime

from pydantic import BaseModel


class PersonalNoteRead(BaseModel):
    id: int
    course_id: int
    target_type: str  # session | file | quiz | text_lesson | assignment
    target_id: int
    note: str | None = None
    attachment: str | None = None
    created_at: datetime
