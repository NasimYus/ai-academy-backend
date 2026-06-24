"""currencies (multi-currency, F.5)

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("currency_position", sa.String(length=20), nullable=False, server_default="left"),
        sa.Column("currency_separator", sa.String(length=8), nullable=False, server_default="dot"),
        sa.Column("currency_decimal", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("exchange_rate", sa.Float(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("currencies")
