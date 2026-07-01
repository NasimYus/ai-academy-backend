"""community forum (categories, topics, posts)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1b2c3d4e5a6"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forums",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("disabled", "active", name="forum_category_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("close", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["parent_id"], ["forums.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_forums_slug"), "forums", ["slug"], unique=True)
    op.create_index(op.f("ix_forums_parent_id"), "forums", ["parent_id"])

    op.create_table(
        "forum_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("forum_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cover", sa.String(length=512), nullable=True),
        sa.Column("pin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("close", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["forum_id"], ["forums.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_forum_topics_slug"), "forum_topics", ["slug"], unique=True)
    op.create_index(op.f("ix_forum_topics_forum_id"), "forum_topics", ["forum_id"])

    op.create_table(
        "forum_topic_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("attach", sa.String(length=512), nullable=True),
        sa.Column("pin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["forum_topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["forum_topic_posts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_forum_topic_posts_topic_id"), "forum_topic_posts", ["topic_id"])


def downgrade() -> None:
    op.drop_table("forum_topic_posts")
    op.drop_table("forum_topics")
    op.drop_table("forums")
    sa.Enum(name="forum_category_status").drop(op.get_bind(), checkfirst=True)
