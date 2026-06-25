"""order_items.bundle_id (paid bundle purchase)

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: str | None = "c6d7e8f9a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("bundle_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_order_items_bundle_id",
        "order_items",
        "bundles",
        ["bundle_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_order_items_bundle_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "bundle_id")
