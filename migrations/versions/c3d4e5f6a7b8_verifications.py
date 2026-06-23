"""verifications table (email/SMS codes)

Revision ID: c3d4e5f6a7b8
Revises: b1a2c3d4e5f6
Create Date: 2026-06-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b1a2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "verifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("mobile", sa.String(length=16), nullable=True),
        sa.Column("email", sa.String(length=64), nullable=True),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verifications_email", "verifications", ["email"])
    op.create_index("ix_verifications_mobile", "verifications", ["mobile"])


def downgrade() -> None:
    op.drop_index("ix_verifications_mobile", table_name="verifications")
    op.drop_index("ix_verifications_email", table_name="verifications")
    op.drop_table("verifications")
