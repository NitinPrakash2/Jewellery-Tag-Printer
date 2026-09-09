"""Initial schema: print_history + app_settings.

Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "print_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("purity_huid", sa.String(length=120), nullable=False),
        sa.Column("product_name", sa.String(length=120), nullable=False),
        sa.Column("gross_weight", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("net_weight", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("copies", sa.Integer(), nullable=False),
        sa.Column("printer_name", sa.String(length=200), nullable=False),
        sa.Column("template_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("printed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_history_product", "print_history", ["product_name"])
    op.create_index("ix_history_printed_at", "print_history", ["printed_at"])
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_history_printed_at", table_name="print_history")
    op.drop_index("ix_history_product", table_name="print_history")
    op.drop_table("print_history")
