"""add source image mime type

Revision ID: 20260612_0004
Revises: 20260611_0003
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260612_0004"
down_revision: Union[str, None] = "20260611_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    if has_table("generation_tasks") and not has_column("generation_tasks", "source_image_mime_type"):
        op.add_column(
            "generation_tasks",
            sa.Column("source_image_mime_type", sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    if has_table("generation_tasks") and has_column("generation_tasks", "source_image_mime_type"):
        op.drop_column("generation_tasks", "source_image_mime_type")
