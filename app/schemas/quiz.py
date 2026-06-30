from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AnswerRead(BaseModel):
    id: int
    title: str | None = None
    correct: bool
    image: str | None = None


class QuestionRead(BaseModel):
    id: int
    title: str
    type: str  # "multiple" | "descriptive"
    descriptive_correct_answer: str | None = None
    grade: int
    negative_grade: int | None = None
    answers: list[AnswerRead] = []


class QuizBrief(BaseModel):
    id: int
    title: str
    time: int
    pass_mark: int
    attempt: int | None = None
    certificate: bool
    status: str
    total_mark: int
    question_count: int
    # auth-scoped (null when anonymous)
    auth_status: str | None = None
    auth_can_start: bool | None = None
    auth_attempt_count: int | None = None
    attempt_state: str | None = None
    count_try_again: int | str | None = None


class QuizDetail(QuizBrief):
    questions: list[QuestionRead] = []


class QuizResultRead(BaseModel):
    id: int
    quiz_id: int
    user_grade: int | None = None
    status: str
    created_at: datetime
    reviewable: bool = False
    answer_sheet: dict[str, Any] | None = None


class MyQuizResultRead(BaseModel):
    """A student's own quiz attempt for the panel `my-results` list."""

    id: int
    quiz_id: int
    quiz_title: str
    course_id: int
    status: str
    user_grade: int | None = None
    created_at: datetime


class OpenQuizRead(BaseModel):
    """An active quiz the student hasn't completed (panel `not participated`)."""

    id: int
    title: str
    course_id: int
    question_count: int


class QuizStartResult(BaseModel):
    quiz_result_id: int
    attempt_number: int
    quiz: QuizDetail


class AnswerSheetItem(BaseModel):
    question_id: int
    # answer id (multiple-choice) or free text (descriptive); null = skipped
    answer: int | str | None = None


class StoreResultRequest(BaseModel):
    quiz_result_id: int
    answer_sheet: list[AnswerSheetItem] = []
