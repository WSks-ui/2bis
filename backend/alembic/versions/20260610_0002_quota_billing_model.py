"""quota billing model

Revision ID: 20260610_0002
Revises: 20260606_0001
Create Date: 2026-06-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260610_0002"
down_revision: Union[str, None] = "20260606_0001"
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


def upgrade() -> None:
    add_column_if_missing("users", sa.Column("subscription_plan", sa.String(length=30), nullable=True))
    add_column_if_missing("users", sa.Column("subscription_period", sa.String(length=20), nullable=True))
    add_column_if_missing(
        "users",
        sa.Column("monthly_quota_total", sa.Integer(), nullable=False, server_default="0"),
    )
    add_column_if_missing(
        "users",
        sa.Column("monthly_quota_remaining", sa.Integer(), nullable=False, server_default="0"),
    )
    add_column_if_missing("users", sa.Column("monthly_quota_reset_at", sa.DateTime(), nullable=True))
    add_column_if_missing(
        "users",
        sa.Column("trial_activated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    add_column_if_missing("users", sa.Column("trial_expire_at", sa.DateTime(), nullable=True))
    add_column_if_missing(
        "users",
        sa.Column("trial_high_quality_used", sa.Integer(), nullable=False, server_default="0"),
    )

    add_column_if_missing("orders", sa.Column("plan_period", sa.String(length=20), nullable=True))
    add_column_if_missing("generation_tasks", sa.Column("balance_source", sa.String(length=20), nullable=True))
    add_column_if_missing("generate_histories", sa.Column("balance_source", sa.String(length=20), nullable=True))


def downgrade() -> None:
    drop_column_if_exists("generate_histories", "balance_source")
    drop_column_if_exists("generation_tasks", "balance_source")
    drop_column_if_exists("orders", "plan_period")
    drop_column_if_exists("users", "trial_high_quality_used")
    drop_column_if_exists("users", "trial_expire_at")
    drop_column_if_exists("users", "trial_activated")
    drop_column_if_exists("users", "monthly_quota_reset_at")
    drop_column_if_exists("users", "monthly_quota_remaining")
    drop_column_if_exists("users", "monthly_quota_total")
    drop_column_if_exists("users", "subscription_period")
    drop_column_if_exists("users", "subscription_plan")
