"""subscriptions (plans + user subscriptions + uses) — Phase 7.2

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-06-25

Parity of `subscribes` / `subscribe_uses` (+ user_subscribes for the purchase,
which legacy derives from a subscribe-type Sale). epoch-int -> timestamptz.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "e2f3a4b5c6d7"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "subscribes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("usable_count", sa.Integer(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column("icon", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_subscribes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subscribe_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscribe_id"], ["subscribes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_subscribes_user_id"), "user_subscribes", ["user_id"])
    op.create_index(op.f("ix_user_subscribes_subscribe_id"), "user_subscribes", ["subscribe_id"])

    op.create_table(
        "subscribe_uses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subscribe_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscribe_id"], ["subscribes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subscribe_uses_user_id"), "subscribe_uses", ["user_id"])
    op.create_index(op.f("ix_subscribe_uses_subscribe_id"), "subscribe_uses", ["subscribe_id"])
    op.create_index(op.f("ix_subscribe_uses_course_id"), "subscribe_uses", ["course_id"])


def downgrade() -> None:
    op.drop_table("subscribe_uses")
    op.drop_table("user_subscribes")
    op.drop_table("subscribes")
