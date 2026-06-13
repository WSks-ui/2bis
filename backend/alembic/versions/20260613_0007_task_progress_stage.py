"""add task progress stage fields

Revision ID: 20260613_0007
Revises: 20260613_0006
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260613_0007"
down_revision: Union[str, None] = "20260613_0006"
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
    if not has_table("generation_tasks"):
        return
    if not has_column("generation_tasks", "progress_stage"):
        op.add_column("generation_tasks", sa.Column("progress_stage", sa.String(length=40), nullable=True))
    if not has_column("generation_tasks", "progress_message"):
        op.add_column("generation_tasks", sa.Column("progress_message", sa.Text(), nullable=True))


def downgrade() -> None:
    if not has_table("generation_tasks"):
        return
    if has_column("generation_tasks", "progress_message"):
        op.drop_column("generation_tasks", "progress_message")
    if has_column("generation_tasks", "progress_stage"):
        op.drop_column("generation_tasks", "progress_stage")
