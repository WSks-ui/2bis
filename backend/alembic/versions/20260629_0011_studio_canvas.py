"""add studio workspace canvas tables

Revision ID: 20260629_0011
Revises: 20260615_0010
Create Date: 2026-06-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260629_0011"
down_revision = "20260615_0010"
branch_labels = None
depends_on = None


def has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not has_table("workspaces"):
        op.create_table(
            "workspaces",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("cover_asset_id", sa.Integer(), nullable=True),
            sa.Column("settings_json", sa.Text(), nullable=False),
            sa.Column("canvas_revision", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("last_opened_at", sa.DateTime(), nullable=True),
            sa.Column("archived_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_workspaces_id", "workspaces", ["id"])
        op.create_index("ix_workspaces_user_id", "workspaces", ["user_id"])
        op.create_index("ix_workspaces_archived_at", "workspaces", ["archived_at"])
        op.create_index("ix_workspaces_deleted_at", "workspaces", ["deleted_at"])

    if not has_table("workspace_assets"):
        op.create_table(
            "workspace_assets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("asset_type", sa.String(length=30), nullable=False),
            sa.Column("source_type", sa.String(length=40), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=True),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("thumbnail_url", sa.Text(), nullable=True),
            sa.Column("mime_type", sa.String(length=80), nullable=True),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("text_content", sa.Text(), nullable=True),
            sa.Column("task_id", sa.Integer(), nullable=True),
            sa.Column("history_id", sa.Integer(), nullable=True),
            sa.Column("parent_asset_id", sa.Integer(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["history_id"], ["generate_histories.id"]),
            sa.ForeignKeyConstraint(["parent_asset_id"], ["workspace_assets.id"]),
            sa.ForeignKeyConstraint(["task_id"], ["generation_tasks.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_workspace_assets_id", "workspace_assets", ["id"])
        op.create_index("ix_workspace_assets_workspace_id", "workspace_assets", ["workspace_id"])
        op.create_index("ix_workspace_assets_user_id", "workspace_assets", ["user_id"])
        op.create_index("ix_workspace_assets_asset_type", "workspace_assets", ["asset_type"])
        op.create_index("ix_workspace_assets_source_type", "workspace_assets", ["source_type"])
        op.create_index("ix_workspace_assets_task_id", "workspace_assets", ["task_id"])
        op.create_index("ix_workspace_assets_history_id", "workspace_assets", ["history_id"])
        op.create_index("ix_workspace_assets_deleted_at", "workspace_assets", ["deleted_at"])

    if not has_table("canvas_items"):
        op.create_table(
            "canvas_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("asset_id", sa.Integer(), nullable=True),
            sa.Column("task_id", sa.Integer(), nullable=True),
            sa.Column("item_type", sa.String(length=30), nullable=False),
            sa.Column("x", sa.Float(), nullable=False),
            sa.Column("y", sa.Float(), nullable=False),
            sa.Column("width", sa.Float(), nullable=False),
            sa.Column("height", sa.Float(), nullable=False),
            sa.Column("rotation", sa.Float(), nullable=False),
            sa.Column("z_index", sa.Integer(), nullable=False),
            sa.Column("locked", sa.Boolean(), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=True),
            sa.Column("data_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["asset_id"], ["workspace_assets.id"]),
            sa.ForeignKeyConstraint(["task_id"], ["generation_tasks.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_canvas_items_id", "canvas_items", ["id"])
        op.create_index("ix_canvas_items_workspace_id", "canvas_items", ["workspace_id"])
        op.create_index("ix_canvas_items_user_id", "canvas_items", ["user_id"])
        op.create_index("ix_canvas_items_asset_id", "canvas_items", ["asset_id"])
        op.create_index("ix_canvas_items_task_id", "canvas_items", ["task_id"])
        op.create_index("ix_canvas_items_item_type", "canvas_items", ["item_type"])
        op.create_index("ix_canvas_items_deleted_at", "canvas_items", ["deleted_at"])

    if not has_table("canvas_relations"):
        op.create_table(
            "canvas_relations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("source_item_id", sa.Integer(), nullable=False),
            sa.Column("target_item_id", sa.Integer(), nullable=False),
            sa.Column("relation_type", sa.String(length=40), nullable=False),
            sa.Column("label", sa.String(length=120), nullable=True),
            sa.Column("strength", sa.Float(), nullable=False),
            sa.Column("data_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["source_item_id"], ["canvas_items.id"]),
            sa.ForeignKeyConstraint(["target_item_id"], ["canvas_items.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_canvas_relations_id", "canvas_relations", ["id"])
        op.create_index("ix_canvas_relations_workspace_id", "canvas_relations", ["workspace_id"])
        op.create_index("ix_canvas_relations_user_id", "canvas_relations", ["user_id"])
        op.create_index("ix_canvas_relations_source_item_id", "canvas_relations", ["source_item_id"])
        op.create_index("ix_canvas_relations_target_item_id", "canvas_relations", ["target_item_id"])
        op.create_index("ix_canvas_relations_relation_type", "canvas_relations", ["relation_type"])
        op.create_index("ix_canvas_relations_deleted_at", "canvas_relations", ["deleted_at"])


def downgrade() -> None:
    for table_name in ("canvas_relations", "canvas_items", "workspace_assets", "workspaces"):
        if has_table(table_name):
            op.drop_table(table_name)
