"""users + roles parity port (legacy schema)

Replaces the skeleton `users` table with the full legacy-parity schema and
adds the `roles` table (seeded with legacy defaults). Greenfield: no data to
preserve, so the old `users` table and `user_role` enum are dropped.

Revision ID: b1a2c3d4e5f6
Revises: 453e4ae9688e
Create Date: 2026-06-22

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1a2c3d4e5f6"
down_revision: str | None = "453e4ae9688e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # Drop the courses FK into users, the skeleton users table, and its enum.
    op.drop_constraint("courses_teacher_id_fkey", "courses", type_="foreignkey")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    sa.Enum(name="user_role").drop(bind, checkfirst=True)

    # --- roles ---
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("caption", sa.String(length=64), nullable=False),
        sa.Column("users_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    roles = sa.table(
        "roles",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("caption", sa.String),
        sa.column("is_admin", sa.Boolean),
    )
    # Legacy default ids: user=1, organization=3, teacher=4 (admin=2).
    op.bulk_insert(
        roles,
        [
            {"id": 1, "name": "user", "caption": "User", "is_admin": False},
            {"id": 2, "name": "admin", "caption": "Admin", "is_admin": True},
            {"id": 3, "name": "organization", "caption": "Organization", "is_admin": False},
            {"id": 4, "name": "teacher", "caption": "Teacher", "is_admin": False},
        ],
    )
    # Advance the identity sequence past the seeded ids.
    op.execute("SELECT setval(pg_get_serial_sequence('roles', 'id'), 4, true)")

    # --- users (full legacy-parity column set) ---
    user_status = sa.Enum("active", "pending", "inactive", name="user_status")
    meeting_type = sa.Enum("all", "in_person", "online", name="meeting_type")
    theme_color_mode = sa.Enum("dark", "light", name="theme_color_mode")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        # identity / login
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("mobile", sa.String(length=32), nullable=True),
        sa.Column("password", sa.String(length=255), nullable=True),
        sa.Column("role_name", sa.String(length=64), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("organ_id", sa.Integer(), nullable=True),
        sa.Column("remember_token", sa.String(length=255), nullable=True),
        sa.Column("google_id", sa.String(length=255), nullable=True),
        sa.Column("facebook_id", sa.String(length=255), nullable=True),
        # status / verification / ban
        sa.Column("status", user_status, nullable=False, server_default="active"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("logged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ban", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ban_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ban_end_at", sa.DateTime(timezone=True), nullable=True),
        # profile
        sa.Column("bio", sa.String(length=48), nullable=True),
        sa.Column("headline", sa.String(length=128), nullable=True),
        sa.Column("about", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("avatar", sa.String(length=128), nullable=True),
        sa.Column("avatar_settings", sa.String(length=255), nullable=True),
        sa.Column("cover_img", sa.String(length=128), nullable=True),
        sa.Column("profile_video", sa.String(length=255), nullable=True),
        sa.Column("profile_secondary_image", sa.String(length=255), nullable=True),
        # preferences
        sa.Column("language", sa.String(length=128), nullable=True),
        sa.Column("currency", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=255), nullable=True),
        sa.Column("theme_color_mode", theme_color_mode, nullable=True),
        sa.Column("newsletter", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("public_message", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "enable_profile_statistics", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "auto_renew_subscription", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("account_type", sa.String(length=128), nullable=True),
        # finance
        sa.Column("financial_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("installment_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enable_installments", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("disable_cashback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("iban", sa.String(length=128), nullable=True),
        sa.Column("account_id", sa.String(length=128), nullable=True),
        sa.Column("commission", sa.Integer(), nullable=True),
        sa.Column("can_create_store", sa.Boolean(), nullable=False, server_default=sa.false()),
        # rewards / affiliate
        sa.Column("affiliate", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "enable_registration_bonus", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("registration_bonus_amount", sa.Numeric(precision=15, scale=2), nullable=True),
        # misc
        sa.Column("access_content", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enable_ai_content", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("group_meeting", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("meeting_type", meeting_type, nullable=False, server_default="all"),
        sa.Column("level_of_training", sa.SmallInteger(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("country_id", sa.Integer(), nullable=True),
        sa.Column("province_id", sa.Integer(), nullable=True),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column("identity_scan", sa.Text(), nullable=True),
        sa.Column("certificate", sa.Text(), nullable=True),
        sa.Column("offline", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("offline_message", sa.Text(), nullable=True),
        # timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_mobile", "users", ["mobile"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # Restore the courses -> users FK.
    op.create_foreign_key(
        "courses_teacher_id_fkey", "courses", "users", ["teacher_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_constraint("courses_teacher_id_fkey", "courses", type_="foreignkey")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_mobile", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    for name in ("user_status", "meeting_type", "theme_color_mode"):
        sa.Enum(name=name).drop(bind, checkfirst=True)
    op.drop_table("roles")

    # Recreate the skeleton users table + enum + FK.
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role", sa.Enum("student", "teacher", "admin", name="user_role"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_foreign_key(
        "courses_teacher_id_fkey", "courses", "users", ["teacher_id"], ["id"], ondelete="SET NULL"
    )
