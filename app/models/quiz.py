import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class QuizStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class QuestionType(str, enum.Enum):
    multiple = "multiple"
    descriptive = "descriptive"


class ResultStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    waiting = "waiting"


class Quiz(Base):
    """Quiz attached to a course (and optionally a chapter), parity of `quizzes`."""

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"), index=True
    )
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    time: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # null attempt == unlimited tries (legacy `isset($this->attempt)`)
    attempt: Mapped[int | None] = mapped_column(Integer)
    pass_mark: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    certificate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[QuizStatus] = mapped_column(
        Enum(QuizStatus, name="quiz_status"), default=QuizStatus.active, nullable=False
    )
    total_mark: Mapped[int | None] = mapped_column(Integer)
    display_limited_questions: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_number_of_questions: Mapped[int | None] = mapped_column(Integer)
    display_questions_randomly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expiry_days: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class QuizQuestion(Base):
    """Quiz question (multiple-choice or descriptive), parity of `quizzes_questions`."""

    __tablename__ = "quizzes_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    grade: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_grade: Mapped[int | None] = mapped_column(Integer)
    type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="quiz_question_type"), nullable=False
    )
    # descriptive correct answer (free text); null for multiple-choice
    correct: Mapped[str | None] = mapped_column(Text)
    image: Mapped[str | None] = mapped_column(String(512))
    video: Mapped[str | None] = mapped_column(String(512))
    order: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    answers: Mapped[list["QuizQuestionAnswer"]] = relationship(
        "QuizQuestionAnswer",
        cascade="all, delete-orphan",
        order_by="QuizQuestionAnswer.id",
    )


class QuizQuestionAnswer(Base):
    """Answer option for a multiple-choice question, parity of `quizzes_questions_answers`."""

    __tablename__ = "quizzes_questions_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes_questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str | None] = mapped_column(String(512))
    image: Mapped[str | None] = mapped_column(String(512))
    correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class QuizResult(Base):
    """One quiz attempt by a user, parity of `quizzes_results`.

    `results` holds the graded answer sheet (JSONB) keyed by question id, mirroring
    the legacy json column.
    """

    __tablename__ = "quizzes_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    results: Mapped[dict | None] = mapped_column(JSONB)
    user_grade: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ResultStatus] = mapped_column(
        Enum(ResultStatus, name="quiz_result_status"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
