"""course wizard fields (locale/summary/icon)

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "b6c7d8e9f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("locale", sa.String(length=8), nullable=True))
    op.add_column("courses", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("courses", sa.Column("icon", sa.String(length=512), nullable=True))
    op.add_column("course_translations", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("course_translations", "summary")
    op.drop_column("courses", "icon")
    op.drop_column("courses", "summary")
    op.drop_column("courses", "locale")
