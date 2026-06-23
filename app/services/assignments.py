"""Assignment student-flow rules — parity of AssignmentHistoryMessageController.

Deadline is measured from the enrollment date (legacy uses the sale date).
Instructor grading / review is Phase 6.
"""

from datetime import UTC, datetime

from app.models.assignment import Assignment, AssignmentHistory, AssignmentHistoryMessage
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.schemas.assignment import (
    AssignmentHistoryRead,
    AssignmentMessageRead,
    AssignmentRead,
    MessageUser,
)

DAY_SECONDS = 60 * 60 * 24


def deadline_state(assignment: Assignment, enrollment: Enrollment | None) -> float | bool:
    """Legacy getAssignmentDeadline: True when open, days-left float, or False (passed)."""
    if not assignment.deadline:
        return True
    if enrollment is None:  # owner / no access-start anchor
        return True
    end = enrollment.created_at.timestamp() + assignment.deadline * DAY_SECONDS
    now = datetime.now(UTC).timestamp()
    if now > end:
        return False
    return round((end - now) / DAY_SECONDS, 1)


def submission_blocked(
    assignment: Assignment, enrollment: Enrollment | None, sender_message_count: int
) -> bool:
    """Legacy: blocked when the deadline passed or attempts are exhausted."""
    if deadline_state(assignment, enrollment) is False:
        return True
    return bool(assignment.attempts) and sender_message_count >= assignment.attempts


def _user(u) -> MessageUser:
    return MessageUser(id=u.id, full_name=u.full_name, avatar=u.avatar)


def assignment_read(assignment: Assignment, course: Course | None) -> AssignmentRead:
    return AssignmentRead(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        course_id=assignment.course_id,
        course_title=course.title if course else None,
        course_image=course.thumbnail if course else None,
        attempts=assignment.attempts,
        pass_grade=assignment.pass_grade,
        total_grade=assignment.grade,
        status=assignment.status.value,
        access_after_day=assignment.access_after_day,
        check_previous_parts=assignment.check_previous_parts,
    )


def history_read(
    history: AssignmentHistory,
    course: Course | None,
    *,
    used_attempts: int,
    deadline: float | bool,
    can_send: bool,
) -> AssignmentHistoryRead:
    a = history.assignment
    return AssignmentHistoryRead(
        id=history.id,
        assignment_id=a.id,
        title=a.title,
        description=a.description,
        course_id=a.course_id,
        course_title=course.title if course else None,
        course_image=course.thumbnail if course else None,
        student=_user(history.student),
        deadline=deadline,
        can_send_message=can_send,
        attempts=a.attempts,
        used_attempts_count=used_attempts,
        grade=history.grade,
        total_grade=a.grade,
        pass_grade=a.pass_grade,
        user_status=history.status.value,
    )


def message_read(msg: AssignmentHistoryMessage, current_user_id: int) -> AssignmentMessageRead:
    mine = msg.sender_id == current_user_id
    who = _user(msg.sender)
    return AssignmentMessageRead(
        id=msg.id,
        sender=who if mine else None,
        supporter=None if mine else who,
        message=msg.message,
        file_title=msg.file_title,
        file_path=msg.file_path,
        created_at=msg.created_at,
    )
