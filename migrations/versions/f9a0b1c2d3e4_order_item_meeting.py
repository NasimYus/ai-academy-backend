"""order_items.reserve_meeting_id + reserve_meetings.sale_id (paid meeting)

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f9a0b1c2d3e4"
down_revision: str | None = "e8f9a0b1c2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("reserve_meeting_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_order_items_reserve_meeting_id",
        "order_items",
        "reserve_meetings",
        ["reserve_meeting_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("reserve_meetings", sa.Column("sale_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_reserve_meetings_sale_id",
        "reserve_meetings",
        "sales",
        ["sale_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_reserve_meetings_sale_id", "reserve_meetings", type_="foreignkey")
    op.drop_column("reserve_meetings", "sale_id")
    op.drop_constraint("fk_order_items_reserve_meeting_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "reserve_meeting_id")
