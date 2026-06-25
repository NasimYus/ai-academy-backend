"""payment_channels: credentials + image + currencies (gateway drivers)

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b5c6d7e8f9a0"
down_revision: str | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payment_channels", sa.Column("image", sa.String(length=512), nullable=True))
    op.add_column(
        "payment_channels",
        sa.Column("credentials", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "payment_channels",
        sa.Column("currencies", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_channels", "currencies")
    op.drop_column("payment_channels", "credentials")
    op.drop_column("payment_channels", "image")
