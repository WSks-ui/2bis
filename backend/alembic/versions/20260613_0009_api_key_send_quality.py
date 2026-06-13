"""add api key send quality option

Revision ID: 20260613_0009
Revises: 20260613_0008
Create Date: 2026-06-13 14:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260613_0009"
down_revision = "20260613_0008"
branch_labels = None
depends_on = None


def has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not has_column("api_key_configs", "send_quality"):
        op.add_column(
            "api_key_configs",
            sa.Column("send_quality", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    if has_column("api_key_configs", "send_quality"):
        op.drop_column("api_key_configs", "send_quality")
