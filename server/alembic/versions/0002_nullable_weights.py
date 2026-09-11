"""Allow blank weights: gross/net become nullable (blank prints nothing).

Names stay NOT NULL (blank stores as ""). Existing NULL-hostile SQLite
files are rebuilt on desktop startup (see desktop._migrate_sqlite).

Revision ID: 0002_nullable_weights
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_nullable_weights"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("print_history") as batch:
        batch.alter_column("gross_weight", existing_type=sa.Numeric(10, 3),
                           nullable=True, existing_nullable=False)
        batch.alter_column("net_weight", existing_type=sa.Numeric(10, 3),
                           nullable=True, existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("print_history") as batch:
        batch.alter_column("gross_weight", existing_type=sa.Numeric(10, 3),
                           nullable=False, existing_nullable=True)
        batch.alter_column("net_weight", existing_type=sa.Numeric(10, 3),
                           nullable=False, existing_nullable=True)
