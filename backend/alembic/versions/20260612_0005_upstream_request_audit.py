"""add upstream request audit fields

Revision ID: 20260612_0005
Revises: 20260612_0004
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260612_0005"
down_revision: Union[str, None] = "20260612_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AUDIT_COLUMNS = (
    sa.Column("upstream_model", sa.String(length=80), nullable=True),
    sa.Column("upstream_endpoint", sa.String(length=120), nullable=True),
    sa.Column("upstream_request_quality", sa.String(length=30), nullable=True),
    sa.Column("upstream_request_size", sa.String(length=40), nullable=True),
    sa.Column("upstream_response_format", sa.String(length=30), nullable=True),
    sa.Column("upstream_request_id", sa.String(length=120), nullable=True),
    sa.Column("upstream_content_type", sa.String(length=120), nullable=True),
    sa.Column("upstream_elapsed_seconds", sa.Float(), nullable=True),
    sa.Column("upstream_payload_length", sa.Integer(), nullable=True),
)


def has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    for table in ("generation_tasks", "generate_histories"):
        if not has_table(table):
            continue
        for column in AUDIT_COLUMNS:
            if not has_column(table, column.name):
                op.add_column(table, column.copy())


def downgrade() -> None:
    for table in ("generate_histories", "generation_tasks"):
        if not has_table(table):
            continue
        for column in reversed(AUDIT_COLUMNS):
            if has_column(table, column.name):
                op.drop_column(table, column.name)
