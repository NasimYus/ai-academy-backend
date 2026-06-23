"""course_reviews + comments

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    review_status = sa.Enum("pending", "active", name="review_status")
    op.create_table(
        "course_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content_quality", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("instructor_skills", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("purchase_worth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("support_quality", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", review_status, nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_reviews_course_id", "course_reviews", ["course_id"])

    comment_status = sa.Enum("open", "replied", "new", name="comment_status")
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reply_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("status", comment_status, nullable=False, server_default="new"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reply_id"], ["comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_course_id", "comments", ["course_id"])
    op.create_index("ix_comments_reply_id", "comments", ["reply_id"])


def downgrade() -> None:
    op.drop_table("comments")
    sa.Enum(name="comment_status").drop(op.get_bind(), checkfirst=True)
    op.drop_table("course_reviews")
    sa.Enum(name="review_status").drop(op.get_bind(), checkfirst=True)
