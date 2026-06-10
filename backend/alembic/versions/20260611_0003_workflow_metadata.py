"""add workflow metadata

Revision ID: 20260611_0003
Revises: 20260610_0002
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_0003"
down_revision: Union[str, None] = "20260610_0002"
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


def add_column_if_missing(table: str, column: sa.Column) -> None:
    if has_table(table) and not has_column(table, column.name):
        op.add_column(table, column)


def drop_column_if_exists(table: str, column: str) -> None:
    if has_table(table) and has_column(table, column):
        op.drop_column(table, column)


def add_workflow_columns(table: str) -> None:
    add_column_if_missing(
        table,
        sa.Column(
            "workflow_type",
            sa.String(length=40),
            nullable=False,
            server_default="standard",
        ),
    )
    add_column_if_missing(
        table,
        sa.Column("workflow_cost", sa.Integer(), nullable=False, server_default="0"),
    )
    add_column_if_missing(table, sa.Column("workflow_preset", sa.String(length=80), nullable=True))


def upgrade() -> None:
    add_workflow_columns("generation_tasks")
    add_workflow_columns("generate_histories")


def downgrade() -> None:
    drop_column_if_exists("generate_histories", "workflow_preset")
    drop_column_if_exists("generate_histories", "workflow_cost")
    drop_column_if_exists("generate_histories", "workflow_type")
    drop_column_if_exists("generation_tasks", "workflow_preset")
    drop_column_if_exists("generation_tasks", "workflow_cost")
    drop_column_if_exists("generation_tasks", "workflow_type")
