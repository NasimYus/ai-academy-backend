"""featured_courses

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    page = sa.Enum("categories", "home", "home_categories", name="featured_page")
    status = sa.Enum("publish", "pending", name="featured_status")
    op.create_table(
        "featured_courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("page", page, nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", status, nullable=False, server_default="pending"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_featured_courses_course_id", "featured_courses", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_featured_courses_course_id", table_name="featured_courses")
    op.drop_table("featured_courses")
    sa.Enum(name="featured_page").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="featured_status").drop(op.get_bind(), checkfirst=True)
