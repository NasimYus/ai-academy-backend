"""orders + order_items (checkout)

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-06-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b0c1d2e3f4a5"
down_revision: str | None = "a9b0c1d2e3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "paying", "paid", "fail", name="order_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "payment_method",
            sa.Enum("credit", "payment_channel", name="payment_method"),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(15, 3), nullable=False),
        sa.Column("tax", sa.Numeric(15, 3), nullable=True),
        sa.Column("total_discount", sa.Numeric(15, 3), nullable=True),
        sa.Column("total_amount", sa.Numeric(15, 3), nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("discount_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(15, 3), nullable=False),
        sa.Column("tax", sa.Numeric(15, 3), nullable=True),
        sa.Column("commission", sa.Numeric(15, 3), nullable=True),
        sa.Column("discount", sa.Numeric(15, 3), nullable=True),
        sa.Column("total_amount", sa.Numeric(15, 3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["discount_id"], ["discounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade() -> None:
    op.drop_table("order_items")
    op.drop_table("orders")
    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS order_status")
