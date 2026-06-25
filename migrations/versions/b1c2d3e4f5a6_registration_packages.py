"""registration_packages + user_registration_packages — Phase 7.4 tail

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-06-25

Parity of `registration_packages` (title/description inline; epoch-int ->
timestamptz). user_registration_packages = the package activation.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "a0b1c2d3e4f5"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "registration_packages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "role", sa.Enum("instructors", "organizations", name="package_role"), nullable=False
        ),
        sa.Column("days", sa.Integer(), nullable=True),
        sa.Column("price", sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column("icon", sa.String(length=512), nullable=True),
        sa.Column("instructors_count", sa.Integer(), nullable=True),
        sa.Column("students_count", sa.Integer(), nullable=True),
        sa.Column("courses_capacity", sa.Integer(), nullable=True),
        sa.Column("courses_count", sa.Integer(), nullable=True),
        sa.Column("meeting_count", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("disabled", "active", name="package_status"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_registration_packages_role"), "registration_packages", ["role"])

    op.create_table(
        "user_registration_packages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["package_id"], ["registration_packages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_registration_packages_user_id"),
        "user_registration_packages",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_user_registration_packages_package_id"),
        "user_registration_packages",
        ["package_id"],
    )


def downgrade() -> None:
    op.drop_table("user_registration_packages")
    op.drop_table("registration_packages")
    op.execute("DROP TYPE IF EXISTS package_role")
    op.execute("DROP TYPE IF EXISTS package_status")
