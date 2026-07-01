"""bundle content fields (summary/description/seo/video/flags)

Revision ID: bundlecf0001
Revises: f1b2c3d4e5a6
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bundlecf0001"
down_revision: str | None = "f1b2c3d4e5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bundles", sa.Column("locale", sa.String(length=8), nullable=True))
    op.add_column("bundles", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("bundles", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("bundles", sa.Column("seo_description", sa.String(length=256), nullable=True))
    op.add_column("bundles", sa.Column("video_demo", sa.String(length=512), nullable=True))
    op.add_column(
        "bundles", sa.Column("video_demo_source", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "bundles",
        sa.Column("private", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "bundles",
        sa.Column("certificate", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "bundles",
        sa.Column("only_for_students", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    for col in (
        "only_for_students",
        "certificate",
        "private",
        "video_demo_source",
        "video_demo",
        "seo_description",
        "description",
        "summary",
        "locale",
    ):
        op.drop_column("bundles", col)
