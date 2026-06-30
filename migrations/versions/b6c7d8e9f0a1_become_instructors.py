"""become_instructors (student → instructor requests)

Revision ID: b6c7d8e9f0a1
Revises: f5a6b7c8d9e0
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b6c7d8e9f0a1"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    status = sa.Enum("pending", "accept", "reject", name="become_instructor_status")
    op.create_table(
        "become_instructors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("occupations", sa.JSON(), nullable=True),
        sa.Column("status", status, nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_become_instructors_user_id"),
    )
    op.create_index("ix_become_instructors_user_id", "become_instructors", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_become_instructors_user_id", table_name="become_instructors")
    op.drop_table("become_instructors")
    sa.Enum(name="become_instructor_status").drop(op.get_bind(), checkfirst=True)
