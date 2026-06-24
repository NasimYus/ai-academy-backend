"""certificates (quiz achievement certificates)

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-06-23

Phase 3.6. Parity of `certificates` (epoch-int created_at -> timestamptz).
"""

import sqlalchemy as sa
from alembic import op

revision: str = "b4c5d6e7f8a9"
down_revision: str | None = "a3b4c5d6e7f8"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quiz_id", sa.Integer(), nullable=False),
        sa.Column("quiz_result_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("user_grade", sa.Integer(), nullable=True),
        sa.Column("file", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quiz_result_id"], ["quizzes_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_certificates_quiz_id"), "certificates", ["quiz_id"])
    op.create_index(op.f("ix_certificates_quiz_result_id"), "certificates", ["quiz_result_id"])
    op.create_index(op.f("ix_certificates_student_id"), "certificates", ["student_id"])


def downgrade() -> None:
    op.drop_table("certificates")
