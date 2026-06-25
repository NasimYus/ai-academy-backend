"""store: product_categories + products — Phase 6.6

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-06-25

Parity of `product_categories` / `products` (title/description inline;
epoch-int -> timestamptz). Catalogue only.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("icon", sa.String(length=512), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_categories_parent_id"), "product_categories", ["parent_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail", sa.String(length=512), nullable=True),
        sa.Column("type", sa.Enum("virtual", "physical", name="product_type"), nullable=False),
        sa.Column("price", sa.Numeric(precision=15, scale=3), nullable=True),
        sa.Column("point", sa.Integer(), nullable=True),
        sa.Column("ordering", sa.Boolean(), nullable=False),
        sa.Column("unlimited_inventory", sa.Boolean(), nullable=False),
        sa.Column("inventory", sa.Integer(), nullable=True),
        sa.Column("delivery_fee", sa.Numeric(precision=15, scale=3), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "pending", "draft", "inactive", name="product_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["product_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_creator_id"), "products", ["creator_id"])
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"])


def downgrade() -> None:
    op.drop_table("products")
    op.drop_table("product_categories")
    op.execute("DROP TYPE IF EXISTS product_type")
    op.execute("DROP TYPE IF EXISTS product_status")
