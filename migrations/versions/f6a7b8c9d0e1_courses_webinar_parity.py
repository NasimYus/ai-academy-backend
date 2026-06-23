"""courses webinar parity (expand Course to legacy Webinar columns)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-23

Phase 2.2. The Phase 0 `courses` table (8 columns, course_status
draft/published/archived) is replaced with the legacy `webinars` shape.
No data to preserve (clean DB), so we drop and recreate.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_courses_slug"), table_name="courses")
    op.drop_table("courses")
    op.execute("DROP TYPE IF EXISTS course_status")  # old enum (draft/published/archived)

    # Create the new enum types explicitly. Alembic memoizes CREATE TYPE per
    # name and the initial migration already "created" `course_status`, so
    # create_table would silently skip it — hence explicit create + create_type=False.
    bind = op.get_bind()
    course_type = postgresql.ENUM("webinar", "course", "text_lesson", name="course_type")
    course_status = postgresql.ENUM(
        "active", "pending", "is_draft", "inactive", name="course_status"
    )
    video_demo_source = postgresql.ENUM(
        "upload", "youtube", "vimeo", "external_link", name="video_demo_source"
    )
    course_type.create(bind, checkfirst=True)
    course_status.create(bind, checkfirst=True)
    video_demo_source.create(bind, checkfirst=True)

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(name="course_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="course_status", create_type=False),
            nullable=False,
        ),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("seo_description", sa.String(length=128), nullable=True),
        sa.Column("thumbnail", sa.String(length=512), nullable=True),
        sa.Column("image_cover", sa.String(length=512), nullable=True),
        sa.Column("video_demo", sa.String(length=512), nullable=True),
        sa.Column(
            "video_demo_source",
            postgresql.ENUM(name="video_demo_source", create_type=False),
            nullable=True,
        ),
        sa.Column("price", sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column("organization_price", sa.Numeric(precision=15, scale=3), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("access_days", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("support", sa.Boolean(), nullable=False),
        sa.Column("subscribe", sa.Boolean(), nullable=False),
        sa.Column("private", sa.Boolean(), nullable=False),
        sa.Column("partner_instructor", sa.Boolean(), nullable=False),
        sa.Column("downloadable", sa.Boolean(), nullable=False),
        sa.Column("certificate", sa.Boolean(), nullable=False),
        sa.Column("forum", sa.Boolean(), nullable=False),
        sa.Column("enable_waitlist", sa.Boolean(), nullable=False),
        sa.Column("only_for_students", sa.Boolean(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_slug"), "courses", ["slug"], unique=True)
    op.create_index(op.f("ix_courses_teacher_id"), "courses", ["teacher_id"], unique=False)
    op.create_index(op.f("ix_courses_creator_id"), "courses", ["creator_id"], unique=False)
    op.create_index(op.f("ix_courses_category_id"), "courses", ["category_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_courses_category_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_creator_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_teacher_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_slug"), table_name="courses")
    op.drop_table("courses")
    op.execute("DROP TYPE IF EXISTS course_type")
    op.execute("DROP TYPE IF EXISTS course_status")
    op.execute("DROP TYPE IF EXISTS video_demo_source")

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail", sa.String(length=512), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="course_status"),
            nullable=False,
        ),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_slug"), "courses", ["slug"], unique=True)
