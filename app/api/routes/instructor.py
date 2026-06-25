from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, require_level
from app.models.assignment import AssignmentHistoryStatus
from app.models.category import Category
from app.models.course import Course, CourseStatus, CourseType
from app.models.quiz import Quiz, QuizStatus
from app.models.user import User
from app.repositories import assignments as assignments_repo
from app.repositories import comments as comments_repo
from app.repositories import courses as courses_repo
from app.repositories import quizzes as quizzes_repo
from app.schemas.common import error_responses
from app.schemas.course import CourseDetail, CourseRead
from app.schemas.instructor import (
    AssignmentDashboard,
    AssignmentHistoryRow,
    CommentReplyInput,
    CourseCreate,
    CourseUpdate,
    GradeInput,
    InstructorAssignmentRow,
    QuizCreate,
    QuizManageRead,
    QuizResultRow,
    QuizResultsOverview,
    QuizUpdate,
    SubmissionMessage,
    SubmissionView,
)
from app.schemas.review import CommentRead
from app.schemas.user import UserBrief
from app.services import blog_presenter
from app.services.course_presenter import to_brief, to_detail

router = APIRouter(prefix="/panel", tags=["instructor"])

# Teacher or organization (legacy api.level-access:teacher).
TeacherUser = Annotated[User, Depends(require_level("teacher"))]

_EDITABLE = (
    "title",
    "type",
    "thumbnail",
    "image_cover",
    "description",
    "category_id",
    "duration",
    "start_date",
    "capacity",
    "seo_description",
    "video_demo",
    "video_demo_source",
    "price",
    "organization_price",
    "points",
    "access_days",
    "private",
    "support",
    "downloadable",
    "partner_instructor",
    "subscribe",
)


async def _ensure_category(db: DbSession, category_id: int | None) -> None:
    if category_id is not None and await db.get(Category, category_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="category_not_found"
        )


@router.get("/classes", response_model=list[CourseRead])
async def my_classes(current_user: TeacherUser, db: DbSession) -> list[CourseRead]:
    """The instructor's own courses (legacy WebinarsController@list)."""
    courses = await courses_repo.list_by_creator(db, current_user.id)
    return [to_brief(c) for c in courses]


@router.post(
    "/webinar",
    response_model=CourseDetail,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_course(payload: CourseCreate, current_user: TeacherUser, db: DbSession):
    """Create a course (legacy WebinarsController@storeAll)."""
    await _ensure_category(db, payload.category_id)
    if payload.type == CourseType.webinar and payload.start_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="start_date_required"
        )

    # Draft unless the T&C were accepted and it wasn't explicitly saved as draft.
    course_status = (
        CourseStatus.pending if payload.rules and not payload.draft else CourseStatus.is_draft
    )
    data = payload.model_dump(exclude={"rules", "draft"})
    course = Course(
        **data,
        creator_id=current_user.id,
        teacher_id=current_user.id,
        status=course_status,
        slug=await courses_repo.unique_slug(db, payload.title),
    )
    course = await courses_repo.create_course(db, course)
    return to_detail(course)


@router.get(
    "/webinar/{course_id}/edit",
    response_model=CourseDetail,
    responses=error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
)
async def edit_course(course_id: int, current_user: TeacherUser, db: DbSession) -> CourseDetail:
    course = await courses_repo.get_owned(db, course_id, current_user.id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return to_detail(course)


@router.put(
    "/webinar/{course_id}",
    response_model=CourseDetail,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def update_course(
    course_id: int, payload: CourseUpdate, current_user: TeacherUser, db: DbSession
) -> CourseDetail:
    course = await courses_repo.get_owned(db, course_id, current_user.id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes:
        await _ensure_category(db, changes["category_id"])
    changes = {k: v for k, v in changes.items() if k in _EDITABLE}
    course = await courses_repo.update_course(db, course, changes)
    return to_detail(course)


@router.delete(
    "/webinar/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
)
async def delete_course(course_id: int, current_user: TeacherUser, db: DbSession) -> None:
    course = await courses_repo.get_owned(db, course_id, current_user.id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    await courses_repo.delete_course(db, course)


# --- Quizzes (Phase 6.2, legacy Instructor\QuizzesController) ---


def _quiz_read(quiz: Quiz) -> QuizManageRead:
    return QuizManageRead(
        id=quiz.id,
        title=quiz.title,
        course_id=quiz.course_id,
        chapter_id=quiz.chapter_id,
        pass_mark=quiz.pass_mark,
        attempt=quiz.attempt,
        time=quiz.time,
        status=quiz.status,
        certificate=quiz.certificate,
        created_at=quiz.created_at,
    )


async def _resolve_quiz_target(
    db: DbSession, payload: QuizCreate, user: User
) -> tuple[int, int | None]:
    """Validate the course is the instructor's; keep chapter only if it belongs to it."""
    course = await courses_repo.get_owned(db, payload.course_id, user.id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    chapter_id = payload.chapter_id
    if chapter_id is not None:
        chapter = await courses_repo.get_chapter(db, chapter_id)
        if chapter is None or chapter.course_id != course.id:
            chapter_id = None  # legacy silently drops a chapter that isn't on the course
    return course.id, chapter_id


@router.get(
    "/quizzes/list",
    response_model=QuizResultsOverview,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def quiz_results(current_user: TeacherUser, db: DbSession) -> QuizResultsOverview:
    """Instructor results dashboard (legacy QuizzesController@results)."""
    quizzes = await quizzes_repo.list_by_creator(db, current_user.id)
    results = await quizzes_repo.results_for_creator(db, current_user.id)
    total = len(results)
    passed = sum(1 for r in results if r.status.value == "passed")
    waiting = sum(1 for r in results if r.status.value == "waiting")
    graded = [r.user_grade for r in results if r.user_grade is not None]
    avg = round(sum(graded) / len(graded), 2) if graded else 0.0
    return QuizResultsOverview(
        quiz_results_count=total,
        passed_count=passed,
        waiting_count=waiting,
        success_rate=round(passed / total * 100) if total else 0,
        avg_grade=avg,
        quizzes=[_quiz_read(q) for q in quizzes],
        results=[
            QuizResultRow(
                id=r.id,
                user=UserBrief.model_validate(r.user) if r.user else None,
                quiz_id=r.quiz_id,
                quiz_title=r.quiz.title if r.quiz else "",
                user_grade=r.user_grade,
                status=r.status.value,
                created_at=r.created_at,
            )
            for r in results
        ],
    )


@router.post(
    "/quizzes",
    response_model=QuizManageRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def create_quiz(
    payload: QuizCreate, current_user: TeacherUser, db: DbSession
) -> QuizManageRead:
    """Create a quiz shell (legacy QuizzesController@store)."""
    course_id, chapter_id = await _resolve_quiz_target(db, payload, current_user)
    quiz = Quiz(
        title=payload.title,
        course_id=course_id,
        chapter_id=chapter_id,
        creator_id=current_user.id,
        pass_mark=payload.pass_mark,
        attempt=payload.attempt,
        time=payload.time or 0,
        certificate=payload.certificate,
        status=QuizStatus.active if payload.active else QuizStatus.inactive,
    )
    quiz = await quizzes_repo.create_quiz(db, quiz)
    return _quiz_read(quiz)


@router.put(
    "/quizzes/{quiz_id}",
    response_model=QuizManageRead,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def update_quiz(
    quiz_id: int, payload: QuizUpdate, current_user: TeacherUser, db: DbSession
) -> QuizManageRead:
    """Update a quiz shell (legacy QuizzesController@update; scoped to the creator)."""
    quiz = await quizzes_repo.get_owned(db, quiz_id, current_user.id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    course_id, chapter_id = await _resolve_quiz_target(db, payload, current_user)
    quiz = await quizzes_repo.update_quiz(
        db,
        quiz,
        {
            "title": payload.title,
            "course_id": course_id,
            "chapter_id": chapter_id,
            "pass_mark": payload.pass_mark,
            "attempt": payload.attempt,
            "time": payload.time or 0,
            "certificate": payload.certificate,
            "status": QuizStatus.active if payload.active else QuizStatus.inactive,
        },
    )
    return _quiz_read(quiz)


@router.delete(
    "/quizzes/{quiz_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def delete_quiz(quiz_id: int, current_user: TeacherUser, db: DbSession) -> None:
    """Delete a quiz (legacy QuizzesController@destroy, creator-scoped)."""
    quiz = await quizzes_repo.get_owned(db, quiz_id, current_user.id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    await quizzes_repo.delete_quiz(db, quiz)


# --- Assignment grading (Phase 6.3, legacy Instructor\AssignmentController) ---
# NOTE: legacy gates these on the `webinar_assignment_status` feature flag; we keep
# assignments ungated (the student flow is too), matching our build.


@router.get(
    "/assignments",
    response_model=AssignmentDashboard,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def assignment_dashboard(current_user: TeacherUser, db: DbSession) -> AssignmentDashboard:
    """Instructor assignments + review counts (legacy AssignmentController@index)."""
    assignments = await assignments_repo.list_by_creator(db, current_user.id)
    histories = await assignments_repo.histories_for_creator(db, creator_id=current_user.id)
    counts = await assignments_repo.message_counts(db, [h.id for h in histories])

    by_assignment: dict[int, list[AssignmentHistoryRow]] = {}
    for h in histories:
        by_assignment.setdefault(h.assignment_id, []).append(
            AssignmentHistoryRow(
                id=h.id,
                student=UserBrief.model_validate(h.student) if h.student else None,
                status=h.status,
                grade=h.grade,
                submissions_count=counts.get(h.id, 0),
                created_at=h.created_at,
            )
        )

    return AssignmentDashboard(
        course_assignments_count=len(assignments),
        pending_reviews_count=sum(
            1 for h in histories if h.status == AssignmentHistoryStatus.pending
        ),
        passed_count=sum(1 for h in histories if h.status == AssignmentHistoryStatus.passed),
        failed_count=sum(1 for h in histories if h.status == AssignmentHistoryStatus.not_passed),
        assignments=[
            InstructorAssignmentRow(
                id=a.id,
                title=a.title,
                course_id=a.course_id,
                pass_grade=a.pass_grade,
                histories=by_assignment.get(a.id, []),
            )
            for a in assignments
        ],
    )


@router.get(
    "/assignments/{assignment_id}/submissions",
    response_model=list[SubmissionView],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def assignment_submissions(
    assignment_id: int, current_user: TeacherUser, db: DbSession
) -> list[SubmissionView]:
    """Student submission threads on one assignment (legacy @submmision)."""
    histories = await assignments_repo.histories_for_assignment(
        db, assignment_id=assignment_id, instructor_id=current_user.id
    )
    views: list[SubmissionView] = []
    for h in histories:
        messages = await assignments_repo.messages_for_history(db, h.id)
        views.append(
            SubmissionView(
                id=h.id,
                student=UserBrief.model_validate(h.student) if h.student else None,
                status=h.status,
                grade=h.grade,
                messages=[
                    SubmissionMessage(
                        id=m.id,
                        sender=UserBrief.model_validate(m.sender) if m.sender else None,
                        message=m.message,
                        file_title=m.file_title,
                        file_path=m.file_path,
                        created_at=m.created_at,
                    )
                    for m in messages
                ],
            )
        )
    return views


@router.post(
    "/assignments/histories/{history_id}/rate",
    response_model=SubmissionView,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def grade_submission(
    history_id: int, payload: GradeInput, current_user: TeacherUser, db: DbSession
) -> SubmissionView:
    """Grade a submission (legacy AssignmentController@setGrade)."""
    history = await assignments_repo.get_history_owned(db, history_id, current_user.id)
    if history is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    pass_grade = history.assignment.pass_grade or 0
    new_status = (
        AssignmentHistoryStatus.passed
        if payload.grade >= pass_grade
        else AssignmentHistoryStatus.not_passed
    )
    history = await assignments_repo.set_grade(db, history, grade=payload.grade, status=new_status)
    # NOTE(5.7): legacy awards PASS_ASSIGNMENT reward points here — earning rules
    # are gated/deferred, so no accounting yet.
    messages = await assignments_repo.messages_for_history(db, history.id)
    student = await db.get(User, history.student_id)
    return SubmissionView(
        id=history.id,
        student=UserBrief.model_validate(student) if student else None,
        status=history.status,
        grade=history.grade,
        messages=[
            SubmissionMessage(
                id=m.id,
                sender=UserBrief.model_validate(m.sender) if m.sender else None,
                message=m.message,
                file_title=m.file_title,
                file_path=m.file_path,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


# --- Comments (Phase 6.4, legacy CommentsController@myClassComments/reply) ---


@router.get(
    "/comments",
    response_model=list[CommentRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def my_class_comments(current_user: TeacherUser, db: DbSession) -> list[CommentRead]:
    """Comments on the instructor's courses, threaded (legacy @myClassComments).

    NOTE: legacy also stamps `viewed_at`; we don't track that column yet.
    """
    comments = await comments_repo.list_for_instructor(db, current_user.id)
    return blog_presenter.comment_tree(comments)


@router.post(
    "/comments/{comment_id}/reply",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def reply_to_comment(
    comment_id: int, payload: CommentReplyInput, current_user: TeacherUser, db: DbSession
) -> dict[str, str]:
    """Reply to a comment on the instructor's course (legacy @reply, scoped)."""
    parent = await comments_repo.get_for_instructor(db, comment_id, current_user.id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    await comments_repo.create_reply(db, parent=parent, user_id=current_user.id, text=payload.reply)
    return {"status": "stored"}
