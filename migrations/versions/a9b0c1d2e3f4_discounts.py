"""discounts + discount_courses/categories/users (coupons)

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-06-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.String(length=255), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("percent", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("max_amount", sa.Integer(), nullable=True),
        sa.Column("minimum_order", sa.Integer(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "user_type",
            sa.Enum("all_users", "special_users", name="discount_user_type"),
            nullable=False,
            server_default="all_users",
        ),
        sa.Column(
            "discount_type",
            sa.Enum("percentage", "fixed_amount", name="discount_type"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "all",
                "course",
                "category",
                "bundle",
                "product",
                "meeting",
                "event",
                "meeting_package",
                name="discount_source",
            ),
            nullable=False,
            server_default="all",
        ),
        sa.Column("for_first_purchase", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discounts_code", "discounts", ["code"], unique=True)

    op.create_table(
        "discount_courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("discount_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["discount_id"], ["discounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discount_courses_discount_id", "discount_courses", ["discount_id"])

    op.create_table(
        "discount_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("discount_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["discount_id"], ["discounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discount_categories_discount_id", "discount_categories", ["discount_id"])

    op.create_table(
        "discount_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("discount_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["discount_id"], ["discounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discount_users_discount_id", "discount_users", ["discount_id"])


def downgrade() -> None:
    op.drop_table("discount_users")
    op.drop_table("discount_categories")
    op.drop_table("discount_courses")
    op.drop_table("discounts")
    op.execute("DROP TYPE IF EXISTS discount_source")
    op.execute("DROP TYPE IF EXISTS discount_type")
    op.execute("DROP TYPE IF EXISTS discount_user_type")
