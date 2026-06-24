from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.quiz import Quiz
from app.models.user import User


class Certificate(Base):
    """A quiz-achievement certificate, parity of `certificates`.

    Issued when a user passes a quiz flagged `certificate`. `file` holds the
    rendered PDF path (generated lazily on first download). Pixel-perfect
    template rendering (CertificateTemplate) is instructor/admin — Phase 6.
    """

    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    quiz_result_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes_results.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_grade: Mapped[int | None] = mapped_column(Integer)
    file: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    student: Mapped[User] = relationship("User", lazy="raise")
    quiz: Mapped[Quiz] = relationship("Quiz", lazy="raise")
