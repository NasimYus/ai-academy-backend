"""blog + blog categories, blog comments on shared table (Phase 5.5)

Revision ID: a8b9c0d1e2f3
Revises: a7b8c9d0e1f3
Create Date: 2026-06-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "a7b8c9d0e1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blog_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "blog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("image", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("visit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enable_comment", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "status",
            sa.Enum("pending", "publish", name="blog_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["blog_categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blog_category_id", "blog", ["category_id"])

    # The comments table is shared (legacy): add blog target, relax course_id.
    op.add_column("comments", sa.Column("blog_id", sa.Integer(), nullable=True))
    op.alter_column("comments", "course_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        "fk_comments_blog_id", "comments", "blog", ["blog_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_comments_blog_id", "comments", ["blog_id"])


def downgrade() -> None:
    op.drop_index("ix_comments_blog_id", table_name="comments")
    op.drop_constraint("fk_comments_blog_id", "comments", type_="foreignkey")
    op.alter_column("comments", "course_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("comments", "blog_id")
    op.drop_table("blog")
    op.drop_table("blog_categories")
    sa.Enum(name="blog_status").drop(op.get_bind(), checkfirst=True)
