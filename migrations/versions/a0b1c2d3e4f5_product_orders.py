"""product_orders + order_items.product_id/product_order_id (paid product)

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: str | None = "f9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS = sa.Enum(
    "pending", "waiting_delivery", "shipped", "success", "canceled", name="product_order_status"
)


def upgrade() -> None:
    op.create_table(
        "product_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=True),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("message_to_seller", sa.Text(), nullable=True),
        sa.Column("tracking_code", sa.String(length=128), nullable=True),
        sa.Column("status", _STATUS, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_orders_product_id", "product_orders", ["product_id"])
    op.create_index("ix_product_orders_buyer_id", "product_orders", ["buyer_id"])

    op.add_column("order_items", sa.Column("product_id", sa.Integer(), nullable=True))
    op.add_column("order_items", sa.Column("product_order_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_order_items_product_id", "order_items", "products", ["product_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_order_items_product_order_id", "order_items", "product_orders",
        ["product_order_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_order_items_product_order_id", "order_items", type_="foreignkey")
    op.drop_constraint("fk_order_items_product_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "product_order_id")
    op.drop_column("order_items", "product_id")
    op.drop_table("product_orders")
    _STATUS.drop(op.get_bind(), checkfirst=True)
