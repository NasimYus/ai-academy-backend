"""order_items.subscribe_id (paid subscription purchase)

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8f9a0b1c2d3"
down_revision: str | None = "d7e8f9a0b1c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("subscribe_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_order_items_subscribe_id",
        "order_items",
        "subscribes",
        ["subscribe_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_order_items_subscribe_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "subscribe_id")
