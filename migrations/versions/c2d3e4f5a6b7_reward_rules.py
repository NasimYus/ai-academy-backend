"""rewards (earning rules) — Phase 5.7 tail

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-06-25

Parity of `rewards` (the point-earning rule table). The ledger
(`rewards_accounting`) already exists from 5.7.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | None = None
depends_on: str | None = None

_TYPES = (
    "account_charge",
    "create_classes",
    "buy",
    "pass_the_quiz",
    "certificate",
    "comment",
    "register",
    "review_courses",
    "instructor_meeting_reserve",
    "student_meeting_reserve",
    "newsletters",
    "badge",
    "referral",
    "learning_progress_100",
    "charge_wallet",
    "buy_store_product",
    "pass_assignment",
    "make_topic",
    "send_post_in_topic",
    "create_blog_by_instructor",
    "comment_for_instructor_blog",
)


def upgrade() -> None:
    op.create_table(
        "rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.Enum(*_TYPES, name="reward_type"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("condition", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rewards_type"), "rewards", ["type"])


def downgrade() -> None:
    op.drop_table("rewards")
    op.execute("DROP TYPE IF EXISTS reward_type")
