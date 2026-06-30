"""add studio context to generation tasks

Revision ID: 20260629_0012
Revises: 20260629_0011
Create Date: 2026-06-29 20:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260629_0012"
down_revision = "20260629_0011"
branch_labels = None
depends_on = None


def has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    if not has_column("generation_tasks", "workspace_id"):
        op.add_column("generation_tasks", sa.Column("workspace_id", sa.Integer(), nullable=True))
        op.create_index("ix_generation_tasks_workspace_id", "generation_tasks", ["workspace_id"])
        if bind.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_generation_tasks_workspace_id_workspaces",
                "generation_tasks",
                "workspaces",
                ["workspace_id"],
                ["id"],
            )
    if not has_column("generation_tasks", "canvas_item_id"):
        op.add_column("generation_tasks", sa.Column("canvas_item_id", sa.Integer(), nullable=True))
        op.create_index("ix_generation_tasks_canvas_item_id", "generation_tasks", ["canvas_item_id"])
    if not has_column("generation_tasks", "studio_source_item_ids_json"):
        op.add_column("generation_tasks", sa.Column("studio_source_item_ids_json", sa.Text(), nullable=True))


def downgrade() -> None:
    if has_column("generation_tasks", "studio_source_item_ids_json"):
        op.drop_column("generation_tasks", "studio_source_item_ids_json")
    if has_column("generation_tasks", "canvas_item_id"):
        op.drop_index("ix_generation_tasks_canvas_item_id", table_name="generation_tasks")
        op.drop_column("generation_tasks", "canvas_item_id")
    if has_column("generation_tasks", "workspace_id"):
        bind = op.get_bind()
        if bind.dialect.name != "sqlite":
            op.drop_constraint("fk_generation_tasks_workspace_id_workspaces", "generation_tasks", type_="foreignkey")
        op.drop_index("ix_generation_tasks_workspace_id", table_name="generation_tasks")
        op.drop_column("generation_tasks", "workspace_id")
