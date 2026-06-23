from datetime import datetime

from pydantic import BaseModel

# Parity with legacy WebinarAssignmentResource / WebinarAssignmentHistoryResource /
# WebinarAssignmentHistoryMessageResource. Instructor-side aggregates and
# attachment uploads are Phase 6; student-flow fields are real.


class MessageUser(BaseModel):
    id: int
    full_name: str | None = None
    avatar: str | None = None


class AssignmentRead(BaseModel):
    """Legacy WebinarAssignmentResource (student view)."""

    id: int
    content_type: str = "assignment"
    title: str
    description: str | None = None
    course_id: int
    course_title: str | None = None
    course_image: str | None = None
    attempts: int | None = None
    pass_grade: int | None = None
    total_grade: int | None = None  # legacy `grade`
    status: str
    access_after_day: int | None = None
    check_previous_parts: bool = False
    attachments: list[dict] = []  # NOTE(6.x) instructor uploads


class AssignmentHistoryRead(BaseModel):
    """Legacy WebinarAssignmentHistoryResource (the student's submission state)."""

    id: int
    assignment_id: int
    title: str
    description: str | None = None
    course_id: int
    course_title: str | None = None
    course_image: str | None = None
    student: MessageUser
    deadline: float | bool | None = None  # days left, or True when no deadline
    can_send_message: bool = True
    attempts: int | None = None
    used_attempts_count: int = 0
    grade: int | None = None  # set by instructor (Phase 6)
    total_grade: int | None = None
    pass_grade: int | None = None
    user_status: str
    attachments: list[dict] = []  # NOTE(6.x)


class AssignmentMessageRead(BaseModel):
    """Legacy WebinarAssignmentHistoryMessageResource (sender/supporter split)."""

    id: int
    sender: MessageUser | None = None  # set when it's the auth user's own message
    supporter: MessageUser | None = None  # set when it's the other party's message
    message: str
    file_title: str | None = None
    file_path: str | None = None
    created_at: datetime


class SubmitMessageRequest(BaseModel):
    message: str
    file_title: str | None = None
