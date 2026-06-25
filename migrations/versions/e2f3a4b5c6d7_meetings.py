"""meetings + meeting_times + reserve_meetings (Phase 7)

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DAY = sa.Enum(
    "saturday",
    "sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    name="meeting_day_label",
)
_STATUS = sa.Enum("open", "finished", "pending", "canceled", name="reserve_meeting_status")
_TYPE = sa.Enum("in_person", "online", name="reserve_meeting_type")


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("discount", sa.Integer(), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meetings_creator_id", "meetings", ["creator_id"])

    op.create_table(
        "meeting_times",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("day_label", _DAY, nullable=False),
        sa.Column("time", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meeting_times_meeting_id", "meeting_times", ["meeting_id"])

    op.create_table(
        "reserve_meetings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("meeting_time_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(length=16), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", _STATUS, nullable=False),
        sa.Column("paid_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount", sa.Integer(), nullable=True),
        sa.Column("meeting_type", _TYPE, nullable=False, server_default="online"),
        sa.Column("student_count", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=512), nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["meeting_time_id"], ["meeting_times.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reserve_meetings_meeting_id", "reserve_meetings", ["meeting_id"])
    op.create_index("ix_reserve_meetings_user_id", "reserve_meetings", ["user_id"])


def downgrade() -> None:
    op.drop_table("reserve_meetings")
    op.drop_table("meeting_times")
    op.drop_table("meetings")
    _TYPE.drop(op.get_bind(), checkfirst=True)
    _STATUS.drop(op.get_bind(), checkfirst=True)
    _DAY.drop(op.get_bind(), checkfirst=True)
