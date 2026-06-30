"""accounting ledger + offline_payments (student wallet)

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    accounting_type = sa.Enum("addiction", "deduction", name="accounting_type")
    type_account = sa.Enum(
        "asset",
        "income",
        "subscribe",
        "promotion",
        "registration_package",
        "installment_payment",
        name="accounting_type_account",
    )
    offline_status = sa.Enum("waiting", "approved", "reject", name="offline_payment_status")

    op.create_table(
        "accounting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("type", accounting_type, nullable=False),
        sa.Column("type_account", type_account, nullable=False, server_default="asset"),
        sa.Column("system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tax", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_user_id", "accounting", ["user_id"])

    op.create_table(
        "offline_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank", sa.String(length=255), nullable=True),
        sa.Column("reference_number", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", offline_status, nullable=False, server_default="waiting"),
        sa.Column("attachment", sa.String(length=512), nullable=True),
        sa.Column("pay_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_offline_payments_user_id", "offline_payments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_offline_payments_user_id", table_name="offline_payments")
    op.drop_table("offline_payments")
    op.drop_index("ix_accounting_user_id", table_name="accounting")
    op.drop_table("accounting")
    sa.Enum(name="offline_payment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="accounting_type_account").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="accounting_type").drop(op.get_bind(), checkfirst=True)
