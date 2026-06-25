"""bundles + bundle_webinars (Phase 6.5)

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c0d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bundles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("thumbnail", sa.String(length=512), nullable=True),
        sa.Column("image_cover", sa.String(length=512), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("subscribe", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("access_days", sa.Integer(), nullable=True),
        sa.Column("message_for_reviewer", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "pending", "is_draft", "inactive", name="bundle_status"),
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
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bundles_creator_id", "bundles", ["creator_id"])
    op.create_index("ix_bundles_teacher_id", "bundles", ["teacher_id"])

    op.create_table(
        "bundle_webinars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("bundle_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bundle_id"], ["bundles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bundle_webinars_bundle_id", "bundle_webinars", ["bundle_id"])
    op.create_index("ix_bundle_webinars_course_id", "bundle_webinars", ["course_id"])


def downgrade() -> None:
    op.drop_table("bundle_webinars")
    op.drop_table("bundles")
    sa.Enum(name="bundle_status").drop(op.get_bind(), checkfirst=True)
