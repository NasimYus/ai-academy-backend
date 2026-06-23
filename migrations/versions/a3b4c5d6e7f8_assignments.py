"""assignments + history + messages (student submission flow)

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-06-23

Phase 3.5. Parity of webinar_assignments / webinar_assignment_history /
webinar_assignment_history_messages (epoch-int created_at -> timestamptz).
"""

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("grade", sa.Integer(), nullable=True),
        sa.Column("pass_grade", sa.Integer(), nullable=True),
        sa.Column("deadline", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=True),
        sa.Column("check_previous_parts", sa.Boolean(), nullable=False),
        sa.Column("access_after_day", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", name="assignment_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assignments_course_id"), "assignments", ["course_id"])
    op.create_index(op.f("ix_assignments_chapter_id"), "assignments", ["chapter_id"])

    op.create_table(
        "assignment_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instructor_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "passed",
                "not_passed",
                "not_submitted",
                name="assignment_history_status",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["instructor_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assignment_history_instructor_id"), "assignment_history", ["instructor_id"]
    )
    op.create_index(op.f("ix_assignment_history_student_id"), "assignment_history", ["student_id"])
    op.create_index(
        op.f("ix_assignment_history_assignment_id"), "assignment_history", ["assignment_id"]
    )

    op.create_table(
        "assignment_history_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_history_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("file_title", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignment_history_id"], ["assignment_history.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assignment_history_messages_assignment_history_id"),
        "assignment_history_messages",
        ["assignment_history_id"],
    )
    op.create_index(
        op.f("ix_assignment_history_messages_sender_id"),
        "assignment_history_messages",
        ["sender_id"],
    )


def downgrade() -> None:
    op.drop_table("assignment_history_messages")
    op.drop_table("assignment_history")
    op.drop_table("assignments")
    op.execute("DROP TYPE IF EXISTS assignment_history_status")
    op.execute("DROP TYPE IF EXISTS assignment_status")
