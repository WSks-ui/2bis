"""add admin api key configs

Revision ID: 20260613_0006
Revises: 20260612_0005
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260613_0006"
down_revision: Union[str, None] = "20260612_0005"
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
    if has_table("users") and not has_column("users", "is_admin"):
        op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False))

    if not has_table("api_key_configs"):
        op.create_table(
            "api_key_configs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False, server_default="aiartmirror"),
            sa.Column("api_url", sa.String(length=255), nullable=False),
            sa.Column("encrypted_api_key", sa.Text(), nullable=False),
            sa.Column("key_mask", sa.String(length=80), nullable=False),
            sa.Column("response_format", sa.String(length=30), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_test_status", sa.String(length=20), nullable=True),
            sa.Column("last_test_message", sa.Text(), nullable=True),
            sa.Column("last_tested_at", sa.DateTime(), nullable=True),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_api_key_configs_id"), "api_key_configs", ["id"], unique=False)
        op.create_index(op.f("ix_api_key_configs_is_active"), "api_key_configs", ["is_active"], unique=False)
        op.create_index(op.f("ix_api_key_configs_is_enabled"), "api_key_configs", ["is_enabled"], unique=False)

    if not has_table("admin_audit_logs"):
        op.create_table(
            "admin_audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("admin_user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("target_type", sa.String(length=60), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_admin_audit_logs_id"), "admin_audit_logs", ["id"], unique=False)
        op.create_index(op.f("ix_admin_audit_logs_admin_user_id"), "admin_audit_logs", ["admin_user_id"], unique=False)
        op.create_index(op.f("ix_admin_audit_logs_action"), "admin_audit_logs", ["action"], unique=False)
        op.create_index(op.f("ix_admin_audit_logs_created_at"), "admin_audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    if has_table("admin_audit_logs"):
        op.drop_index(op.f("ix_admin_audit_logs_created_at"), table_name="admin_audit_logs")
        op.drop_index(op.f("ix_admin_audit_logs_action"), table_name="admin_audit_logs")
        op.drop_index(op.f("ix_admin_audit_logs_admin_user_id"), table_name="admin_audit_logs")
        op.drop_index(op.f("ix_admin_audit_logs_id"), table_name="admin_audit_logs")
        op.drop_table("admin_audit_logs")

    if has_table("api_key_configs"):
        op.drop_index(op.f("ix_api_key_configs_is_enabled"), table_name="api_key_configs")
        op.drop_index(op.f("ix_api_key_configs_is_active"), table_name="api_key_configs")
        op.drop_index(op.f("ix_api_key_configs_id"), table_name="api_key_configs")
        op.drop_table("api_key_configs")

    if has_table("users") and has_column("users", "is_admin"):
        op.drop_column("users", "is_admin")
