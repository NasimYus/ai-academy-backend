"""quizzes, questions, answers, results

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("time", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt", sa.Integer(), nullable=True),
        sa.Column("pass_mark", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("certificate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", name="quiz_status"),
            nullable=False,
        ),
        sa.Column("total_mark", sa.Integer(), nullable=True),
        sa.Column(
            "display_limited_questions", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("display_number_of_questions", sa.Integer(), nullable=True),
        sa.Column(
            "display_questions_randomly", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("expiry_days", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quizzes_course_id", "quizzes", ["course_id"])
    op.create_index("ix_quizzes_chapter_id", "quizzes", ["chapter_id"])

    op.create_table(
        "quizzes_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quiz_id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("negative_grade", sa.Integer(), nullable=True),
        sa.Column(
            "type",
            sa.Enum("multiple", "descriptive", name="quiz_question_type"),
            nullable=False,
        ),
        sa.Column("correct", sa.Text(), nullable=True),
        sa.Column("image", sa.String(length=512), nullable=True),
        sa.Column("video", sa.String(length=512), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quizzes_questions_quiz_id", "quizzes_questions", ["quiz_id"])

    op.create_table(
        "quizzes_questions_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("image", sa.String(length=512), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["question_id"], ["quizzes_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_quizzes_questions_answers_question_id", "quizzes_questions_answers", ["question_id"]
    )

    op.create_table(
        "quizzes_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quiz_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_grade", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("passed", "failed", "waiting", name="quiz_result_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quizzes_results_quiz_id", "quizzes_results", ["quiz_id"])
    op.create_index("ix_quizzes_results_user_id", "quizzes_results", ["user_id"])


def downgrade() -> None:
    op.drop_table("quizzes_results")
    op.drop_table("quizzes_questions_answers")
    op.drop_table("quizzes_questions")
    op.drop_table("quizzes")
    op.execute("DROP TYPE IF EXISTS quiz_result_status")
    op.execute("DROP TYPE IF EXISTS quiz_question_type")
    op.execute("DROP TYPE IF EXISTS quiz_status")
