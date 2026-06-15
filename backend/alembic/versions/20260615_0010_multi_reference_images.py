"""add multi reference image fields

Revision ID: 20260615_0010
Revises: 20260613_0009
Create Date: 2026-06-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260615_0010"
down_revision = "20260613_0009"
branch_labels = None
depends_on = None


def has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not has_column("generation_tasks", "source_image_paths"):
        op.add_column("generation_tasks", sa.Column("source_image_paths", sa.Text(), nullable=True))
    if not has_column("generation_tasks", "source_image_mime_types"):
        op.add_column("generation_tasks", sa.Column("source_image_mime_types", sa.Text(), nullable=True))


def downgrade() -> None:
    if has_column("generation_tasks", "source_image_mime_types"):
        op.drop_column("generation_tasks", "source_image_mime_types")
    if has_column("generation_tasks", "source_image_paths"):
        op.drop_column("generation_tasks", "source_image_paths")
