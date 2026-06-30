from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models.quiz import ResultStatus
from app.models.reward import RewardType
from app.repositories import courses as courses_repo
from app.repositories import enrollments as enrollments_repo
from app.repositories import quizzes as quizzes_repo
from app.schemas.common import error_responses
from app.schemas.quiz import (
    MyQuizResultRead,
    OpenQuizRead,
    QuizDetail,
    QuizResultRead,
    QuizStartResult,
    StoreResultRequest,
)
from app.services import access
from app.services import certificates as certificates_service
from app.services import quizzes as quiz_service
from app.services import rewards as rewards_service

router = APIRouter(tags=["quizzes"])


@router.get(
    "/courses/{course_id}/quizzes",
    response_model=list[QuizDetail],
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def list_course_quizzes(
    course_id: int, db: DbSession, current_user: OptionalUser
) -> list[QuizDetail]:
    """Active quizzes for a course (legacy WebinarContentController@quizzes)."""
    course = await courses_repo.get_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    has_access = await access.has_course_access(db, current_user, course)
    quizzes = await quizzes_repo.active_for_course(db, course_id)
    return [await quiz_service.build_detail(db, q, current_user, has_access) for q in quizzes]


@router.get(
    "/panel/quizzes/my-results",
    response_model=list[MyQuizResultRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def my_quiz_results(current_user: CurrentUser, db: DbSession) -> list[MyQuizResultRead]:
    """The student's quiz attempts across enrolled courses (legacy my-results)."""
    course_ids = await enrollments_repo.course_ids_for_user(db, current_user.id)
    results = await quizzes_repo.results_for_user_in_courses(db, current_user.id, course_ids)
    return [
        MyQuizResultRead(
            id=r.id,
            quiz_id=r.quiz_id,
            quiz_title=r.quiz.title,
            course_id=r.quiz.course_id,
            status=r.status.value,
            user_grade=r.user_grade,
            created_at=r.created_at,
        )
        for r in results
    ]


@router.get(
    "/panel/quizzes/opens",
    response_model=list[OpenQuizRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def open_quizzes(current_user: CurrentUser, db: DbSession) -> list[OpenQuizRead]:
    """Active quizzes in enrolled courses the student hasn't completed (legacy opens)."""
    course_ids = await enrollments_repo.course_ids_for_user(db, current_user.id)
    quizzes = await quizzes_repo.open_quizzes_for_user(db, current_user.id, course_ids)
    counts = await quizzes_repo.question_counts(db, [q.id for q in quizzes])
    return [
        OpenQuizRead(
            id=q.id, title=q.title, course_id=q.course_id, question_count=counts.get(q.id, 0)
        )
        for q in quizzes
    ]


@router.get(
    "/quizzes/results/{quiz_result_id}/status",
    response_model=QuizResultRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def result_status(
    quiz_result_id: int, current_user: CurrentUser, db: DbSession
) -> QuizResultRead:
    """A user's own quiz result (legacy QuizzesResultController@status)."""
    result = await quizzes_repo.get_user_result(db, quiz_result_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    return quiz_service.result_read(result)


@router.get(
    "/quizzes/{quiz_id}",
    response_model=QuizDetail,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def show_quiz(quiz_id: int, db: DbSession, current_user: OptionalUser) -> QuizDetail:
    """An active quiz with its questions (legacy QuizzesController@show)."""
    quiz = await quizzes_repo.get_active(db, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    course = await courses_repo.get_by_id(db, quiz.course_id)
    has_access = await access.has_course_access(db, current_user, course) if course else False
    return await quiz_service.build_detail(db, quiz, current_user, has_access)


@router.get(
    "/quizzes/{quiz_id}/start",
    response_model=QuizStartResult,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def start_quiz(quiz_id: int, current_user: CurrentUser, db: DbSession) -> QuizStartResult:
    """Begin an attempt: gate then create a waiting result (legacy start)."""
    quiz = await quizzes_repo.get_by_id(db, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    course = await courses_repo.get_by_id(db, quiz.course_id)
    has_access = await access.has_course_access(db, current_user, course) if course else False

    results = await quizzes_repo.user_results(db, quiz.id, current_user.id)
    attempt_count = len(results)
    passed = any(r.status == ResultStatus.passed for r in results)
    take = quiz_service.take_status(
        has_access=has_access, passed=passed, attempt=quiz.attempt, attempt_count=attempt_count
    )
    if take != "ok":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=take)

    new_result = await quizzes_repo.create_result(
        db, quiz_id=quiz.id, user_id=current_user.id, status=ResultStatus.waiting
    )
    detail = await quiz_service.build_detail(db, quiz, current_user, has_access)
    return QuizStartResult(
        quiz_result_id=new_result.id, attempt_number=attempt_count + 1, quiz=detail
    )


@router.post(
    "/quizzes/{quiz_id}/store-result",
    response_model=QuizResultRead,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def store_result(
    quiz_id: int, payload: StoreResultRequest, current_user: CurrentUser, db: DbSession
) -> QuizResultRead:
    """Grade and persist an attempt (legacy quizzesStoreResult)."""
    quiz = await quizzes_repo.get_by_id(db, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    result = await quizzes_repo.get_user_result(db, payload.quiz_result_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    for item in payload.answer_sheet:
        if await quizzes_repo.get_question(db, item.question_id, quiz.id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Question does not belong to this quiz",
            )

    attempt_count = await quizzes_repo.count_results(db, quiz.id, current_user.id)
    results_json, total_mark, new_status = await quiz_service.grade(
        db, quiz, payload.answer_sheet, attempt_count=attempt_count
    )

    result.results = results_json
    result.user_grade = total_mark
    result.status = new_status
    await db.commit()
    await db.refresh(result)

    # Issue an achievement certificate when a certificate-quiz is passed (Phase 3.6).
    await certificates_service.issue_if_passed(db, quiz, result)

    # Award points for passing the quiz (once per quiz; gate + rule honoured).
    if result.status == ResultStatus.passed:
        await rewards_service.award_for(
            db,
            user_id=current_user.id,
            reward_type=RewardType.pass_the_quiz,
            item_id=quiz.id,
            check_duplicate=True,
        )

    return quiz_service.result_read(result)


@router.get(
    "/quizzes/{quiz_id}/result",
    response_model=QuizResultRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def result_by_quiz(quiz_id: int, current_user: CurrentUser, db: DbSession) -> QuizResultRead:
    """A user's passed-or-latest result for a quiz (legacy resultsByQuiz)."""
    result = await quizzes_repo.result_for_quiz(db, quiz_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    return quiz_service.result_read(result)
