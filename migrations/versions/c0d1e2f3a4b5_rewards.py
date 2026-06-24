"""rewards_accounting (points ledger) — Phase 5.7

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-06-24

Parity of `rewards_accounting`. Also adds a `reward` value to the
`enrollment_source` enum (course redeemed with points).
"""

import sqlalchemy as sa
from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: str | None = "b9c0d1e2f3a4"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "rewards_accounting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("addiction", "deduction", name="reward_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rewards_accounting_user_id"), "rewards_accounting", ["user_id"])

    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE enrollment_source ADD VALUE IF NOT EXISTS 'reward'")


def downgrade() -> None:
    op.drop_table("rewards_accounting")
    op.execute("DROP TYPE IF EXISTS reward_status")
    # Note: the 'reward' value on enrollment_source is left in place (Postgres
    # cannot drop a single enum value without recreating the type).
