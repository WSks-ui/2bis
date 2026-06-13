"""add api key circuit breaker fields

Revision ID: 20260613_0008
Revises: 20260613_0007
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260613_0008"
down_revision: Union[str, None] = "20260613_0007"
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
    if not has_table("api_key_configs"):
        return
    if not has_column("api_key_configs", "circuit_state"):
        op.add_column(
            "api_key_configs",
            sa.Column("circuit_state", sa.String(length=20), nullable=False, server_default="closed"),
        )
    if not has_column("api_key_configs", "circuit_reason"):
        op.add_column("api_key_configs", sa.Column("circuit_reason", sa.Text(), nullable=True))
    if not has_column("api_key_configs", "circuit_open_until"):
        op.add_column("api_key_configs", sa.Column("circuit_open_until", sa.DateTime(), nullable=True))
    if not has_column("api_key_configs", "failure_count"):
        op.add_column(
            "api_key_configs",
            sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if not has_column("api_key_configs", "last_failure_at"):
        op.add_column("api_key_configs", sa.Column("last_failure_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    if not has_table("api_key_configs"):
        return
    if has_column("api_key_configs", "last_failure_at"):
        op.drop_column("api_key_configs", "last_failure_at")
    if has_column("api_key_configs", "failure_count"):
        op.drop_column("api_key_configs", "failure_count")
    if has_column("api_key_configs", "circuit_open_until"):
        op.drop_column("api_key_configs", "circuit_open_until")
    if has_column("api_key_configs", "circuit_reason"):
        op.drop_column("api_key_configs", "circuit_reason")
    if has_column("api_key_configs", "circuit_state"):
        op.drop_column("api_key_configs", "circuit_state")
