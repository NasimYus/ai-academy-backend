"""Quiz student-flow logic — parity of legacy QuizzesResultController grading
and the Api\\Quiz auth_* accessors. Instructor review, rewards (Phase 5),
certificate issuance (3.6) and notifications are deferred / gated.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz import QuestionType, QuizQuestion, QuizResult, ResultStatus
from app.models.quiz import Quiz as QuizModel
from app.models.user import User
from app.repositories import quizzes as quizzes_repo
from app.schemas.quiz import AnswerRead, QuestionRead, QuizDetail, QuizResultRead


def take_status(*, has_access: bool, passed: bool, attempt: int | None, attempt_count: int) -> str:
    """Legacy Quiz::auth_can_take_quiz_status."""
    if not has_access:
        return "not_purchased"
    if passed:
        return "passed"
    if attempt is not None and attempt_count >= attempt:
        return "max_attempt"
    return "ok"


def _question_read(question: QuizQuestion) -> QuestionRead:
    return QuestionRead(
        id=question.id,
        title=question.title,
        type=question.type.value,
        descriptive_correct_answer=question.correct,
        grade=question.grade,
        negative_grade=question.negative_grade,
        answers=[
            AnswerRead(id=a.id, title=a.title, correct=a.correct, image=a.image)
            for a in question.answers
        ],
    )


def result_read(result: QuizResult) -> QuizResultRead:
    reviewable = result.status == ResultStatus.waiting and bool(result.results)
    return QuizResultRead(
        id=result.id,
        quiz_id=result.quiz_id,
        user_grade=result.user_grade,
        status=result.status.value,
        created_at=result.created_at,
        reviewable=reviewable,
        answer_sheet=result.results,
    )


async def build_detail(
    db: AsyncSession,
    quiz: QuizModel,
    user: User | None,
    has_access: bool,
    questions: list[QuizQuestion] | None = None,
) -> QuizDetail:
    if questions is None:
        questions = await quizzes_repo.questions_with_answers(db, quiz.id)
    total_mark = sum(q.grade for q in questions)
    question_count = len(questions)

    auth_status: str | None = None
    auth_can_start: bool | None = None
    auth_attempt_count: int | None = None
    attempt_state: str | None = None
    count_try_again: int | str | None = None

    if user is not None:
        results = await quizzes_repo.user_results(db, quiz.id, user.id)  # newest first
        attempt_count = len(results)
        passed = any(r.status == ResultStatus.passed for r in results)
        auth_attempt_count = attempt_count

        if not results:
            auth_status = "not_participated"
        elif passed:
            auth_status = "passed"
        elif results[0].status == ResultStatus.waiting:
            auth_status = "waiting"
        elif results[0].status == ResultStatus.failed:
            auth_status = "failed"

        status = take_status(
            has_access=has_access, passed=passed, attempt=quiz.attempt, attempt_count=attempt_count
        )
        auth_can_start = status == "ok"
        attempt_state = f"{attempt_count}/{quiz.attempt if quiz.attempt is not None else ''}"
        if not auth_can_start:
            count_try_again = 0
        elif quiz.attempt is None:
            count_try_again = "unlimited"
        else:
            diff = quiz.attempt - attempt_count
            count_try_again = diff if diff >= 0 else 0

    return QuizDetail(
        id=quiz.id,
        title=quiz.title,
        time=quiz.time,
        pass_mark=quiz.pass_mark,
        attempt=quiz.attempt,
        certificate=quiz.certificate,
        status=quiz.status.value,
        total_mark=total_mark,
        question_count=question_count,
        auth_status=auth_status,
        auth_can_start=auth_can_start,
        auth_attempt_count=auth_attempt_count,
        attempt_state=attempt_state,
        count_try_again=count_try_again,
        questions=[_question_read(q) for q in questions],
    )


async def grade(
    db: AsyncSession,
    quiz: QuizModel,
    answer_sheet: list,
    *,
    attempt_count: int,
) -> tuple[dict[str, Any], int, ResultStatus]:
    """Grade an answer sheet, parity of QuizzesResultController@quizzesStoreResult.

    Returns (results_json, total_mark, status). Descriptive questions force the
    whole result to `waiting` for instructor review (deferred).
    """
    results: dict[str, Any] = {
        str(item.question_id): {"answer": item.answer} for item in answer_sheet
    }

    total_mark = 0
    has_descriptive = False

    for qid_str, result in results.items():
        answer_value = result.get("answer")
        question = await quizzes_repo.get_question(db, int(qid_str), quiz.id)
        if question is None or answer_value in (None, ""):
            continue

        result["status"] = False
        result["grade"] = question.grade
        result["negative_grade"] = question.negative_grade

        answer = None
        if isinstance(answer_value, int) or (
            isinstance(answer_value, str) and answer_value.isdigit()
        ):
            answer = await quizzes_repo.find_answer(
                db, int(answer_value), question.id, quiz.creator_id
            )

        if answer is not None and answer.correct:
            result["status"] = True
            total_mark += int(question.grade)
        elif question.type == QuestionType.multiple and question.negative_grade:
            total_mark -= int(question.negative_grade)

        if question.type == QuestionType.descriptive:
            has_descriptive = True

    if has_descriptive:
        status = ResultStatus.waiting
    else:
        status = ResultStatus.passed if total_mark >= quiz.pass_mark else ResultStatus.failed

    results["attempt_number"] = attempt_count
    return results, total_mark, status
