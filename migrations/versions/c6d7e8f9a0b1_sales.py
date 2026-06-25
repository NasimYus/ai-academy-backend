"""sales accounting table (parity of legacy sales / Sale::createSales)

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c6d7e8f9a0b1"
down_revision: str | None = "b5c6d7e8f9a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TYPE = sa.Enum(
    "webinar",
    "meeting",
    "subscribe",
    "promotion",
    "registration_package",
    "product",
    "bundle",
    "gift",
    "installment_payment",
    name="sale_type",
)


def upgrade() -> None:
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("type", _TYPE, nullable=False),
        # payment_method enum already exists from the orders migration.
        sa.Column(
            "payment_method",
            sa.Enum("credit", "payment_channel", name="payment_method", create_type=False),
            nullable=True,
        ),
        sa.Column("webinar_id", sa.Integer(), nullable=True),
        sa.Column("bundle_id", sa.Integer(), nullable=True),
        sa.Column("subscribe_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("reserve_meeting_id", sa.Integer(), nullable=True),
        sa.Column("meeting_id", sa.Integer(), nullable=True),
        sa.Column("meeting_time_id", sa.Integer(), nullable=True),
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
        sa.Column("refund_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["webinar_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bundle_id"], ["bundles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subscribe_id"], ["subscribes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reserve_meeting_id"], ["reserve_meetings.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["meeting_time_id"], ["meeting_times.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_buyer_id", "sales", ["buyer_id"])
    op.create_index("ix_sales_seller_id", "sales", ["seller_id"])
    op.create_index("ix_sales_order_id", "sales", ["order_id"])


def downgrade() -> None:
    op.drop_table("sales")
    _TYPE.drop(op.get_bind(), checkfirst=True)
