from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.models.assignment import AssignmentHistoryStatus
from app.repositories import assignments as assignments_repo
from app.repositories import courses as courses_repo
from app.repositories import enrollments as enrollments_repo
from app.schemas.assignment import (
    AssignmentHistoryRead,
    AssignmentMessageRead,
    AssignmentRead,
)
from app.schemas.common import error_responses
from app.services import access, storage
from app.services import assignments as assignment_service

router = APIRouter(tags=["assignments"])


async def _history_read(db: DbSession, history, current_user) -> AssignmentHistoryRead:
    assignment = history.assignment
    course = await courses_repo.get_by_id(db, assignment.course_id)
    enrollment = await enrollments_repo.get(
        db, user_id=current_user.id, course_id=assignment.course_id
    )
    used = await assignments_repo.count_sender_messages(
        db, history_id=history.id, sender_id=current_user.id
    )
    deadline = assignment_service.deadline_state(assignment, enrollment)
    can_send = not assignment_service.submission_blocked(assignment, enrollment, used)
    return assignment_service.history_read(
        history, course, used_attempts=used, deadline=deadline, can_send=can_send
    )


@router.get(
    "/courses/{course_id}/assignments",
    response_model=list[AssignmentRead],
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def list_course_assignments(course_id: int, db: DbSession) -> list[AssignmentRead]:
    """Active assignments of a course (discovery, like course quizzes)."""
    course = await courses_repo.get_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    assignments = await assignments_repo.active_for_course(db, course_id)
    return [assignment_service.assignment_read(a, course) for a in assignments]


@router.get(
    "/panel/my_assignments",
    response_model=list[AssignmentHistoryRead],
)
async def my_assignments(current_user: CurrentUser, db: DbSession) -> list[AssignmentHistoryRead]:
    """The auth user's submission threads across enrolled courses (legacy index)."""
    course_ids = await enrollments_repo.course_ids_for_user(db, current_user.id)
    histories = await assignments_repo.histories_for_student(
        db, student_id=current_user.id, course_ids=course_ids
    )
    return [await _history_read(db, h, current_user) for h in histories]


@router.get(
    "/panel/my_assignments/{assignment_id}",
    response_model=AssignmentHistoryRead,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def my_assignment(
    assignment_id: int, current_user: CurrentUser, db: DbSession
) -> AssignmentHistoryRead:
    history = await assignments_repo.get_history(
        db, assignment_id=assignment_id, student_id=current_user.id
    )
    if history is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not submitted yet")
    return await _history_read(db, history, current_user)


@router.get(
    "/assignments/{assignment_id}",
    response_model=AssignmentRead,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def show_assignment(assignment_id: int, db: DbSession) -> AssignmentRead:
    """Assignment definition (legacy WebinarAssignmentController@show)."""
    assignment = await assignments_repo.get_active(db, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    course = await courses_repo.get_by_id(db, assignment.course_id)
    return assignment_service.assignment_read(assignment, course)


async def _get_or_create_history(db: DbSession, assignment, course, current_user):
    history = await assignments_repo.get_history(
        db, assignment_id=assignment.id, student_id=current_user.id
    )
    if history is not None:
        return history
    instructor_id = assignment.creator_id or (course.teacher_id if course else None)
    if instructor_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Assignment has no instructor"
        )
    return await assignments_repo.create_history(
        db,
        instructor_id=instructor_id,
        student_id=current_user.id,
        assignment_id=assignment.id,
        status=AssignmentHistoryStatus.not_submitted,
    )


@router.get(
    "/assignments/{assignment_id}/messages",
    response_model=list[AssignmentMessageRead],
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def list_messages(
    assignment_id: int, current_user: CurrentUser, db: DbSession
) -> list[AssignmentMessageRead]:
    assignment = await assignments_repo.get_active(db, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    course = await courses_repo.get_by_id(db, assignment.course_id)
    history = await _get_or_create_history(db, assignment, course, current_user)
    messages = await assignments_repo.messages_for_history(db, history.id)
    return [assignment_service.message_read(m, current_user.id) for m in messages]


@router.post(
    "/assignments/{assignment_id}/messages",
    response_model=AssignmentMessageRead,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def submit_message(
    assignment_id: int,
    current_user: CurrentUser,
    db: DbSession,
    message: Annotated[str, Form()],
    file_title: Annotated[str | None, Form()] = None,
    attachment: UploadFile | None = None,
) -> AssignmentMessageRead:
    """Post a submission/message (legacy AssignmentHistoryMessageController@store)."""
    assignment = await assignments_repo.get_active(db, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    course = await courses_repo.get_by_id(db, assignment.course_id)
    if not await access.has_course_access(db, current_user, course):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_purchased")

    history = await _get_or_create_history(db, assignment, course, current_user)

    if current_user.id != assignment.creator_id:
        enrollment = await enrollments_repo.get(
            db, user_id=current_user.id, course_id=assignment.course_id
        )
        used = await assignments_repo.count_sender_messages(
            db, history_id=history.id, sender_id=current_user.id
        )
        if assignment_service.submission_blocked(assignment, enrollment, used):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="assignment_deadline_or_attempts"
            )

    file_path = None
    if attachment is not None:
        file_path = storage.save_upload(attachment, f"assignments/{history.id}")

    msg = await assignments_repo.create_message(
        db,
        history_id=history.id,
        sender_id=current_user.id,
        message=message,
        file_title=file_title,
        file_path=file_path,
    )

    if history.status == AssignmentHistoryStatus.not_submitted:
        history.status = AssignmentHistoryStatus.pending
        await db.commit()

    return assignment_service.message_read(msg, current_user.id)
