"""add local edit mask fields

Revision ID: 20260630_0013
Revises: 20260629_0012
Create Date: 2026-06-30 21:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260630_0013"
down_revision = "20260629_0012"
branch_labels = None
depends_on = None


def has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not has_column("generation_tasks", "source_mask_path"):
        op.add_column("generation_tasks", sa.Column("source_mask_path", sa.Text(), nullable=True))
    if not has_column("generation_tasks", "source_mask_mime_type"):
        op.add_column("generation_tasks", sa.Column("source_mask_mime_type", sa.String(length=50), nullable=True))


def downgrade() -> None:
    if has_column("generation_tasks", "source_mask_mime_type"):
        op.drop_column("generation_tasks", "source_mask_mime_type")
    if has_column("generation_tasks", "source_mask_path"):
        op.drop_column("generation_tasks", "source_mask_path")
