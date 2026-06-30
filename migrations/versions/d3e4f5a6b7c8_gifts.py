"""gifts + order_items.gift_id + sales.gift_id (gift a course/bundle)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS = sa.Enum("pending", "active", "cancel", name="gift_status")


def upgrade() -> None:
    op.create_table(
        "gifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("webinar_id", sa.Integer(), nullable=True),
        sa.Column("bundle_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", _STATUS, nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["webinar_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bundle_id"], ["bundles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sales.id"], ondelete="SET NULL", use_alter=True, name="fk_gifts_sale_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gifts_user_id", "gifts", ["user_id"])
    op.create_index("ix_gifts_email", "gifts", ["email"])

    op.add_column("order_items", sa.Column("gift_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_order_items_gift_id", "order_items", "gifts", ["gift_id"], ["id"], ondelete="SET NULL"
    )
    op.add_column("sales", sa.Column("gift_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_sales_gift_id", "sales", "gifts", ["gift_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_sales_gift_id", "sales", type_="foreignkey")
    op.drop_column("sales", "gift_id")
    op.drop_constraint("fk_order_items_gift_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "gift_id")
    op.drop_constraint("fk_gifts_sale_id", "gifts", type_="foreignkey")
    op.drop_table("gifts")
    _STATUS.drop(op.get_bind(), checkfirst=True)
