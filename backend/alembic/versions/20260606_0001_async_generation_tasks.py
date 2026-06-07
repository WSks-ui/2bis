"""async generation tasks

Revision ID: 20260606_0001
Revises:
Create Date: 2026-06-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260606_0001"
down_revision: Union[str, None] = None
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


def has_index(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    if is_postgresql:
        task_status = sa.Enum("PENDING", "PROCESSING", "SUCCESS", "FAILED", "REFUNDED", name="generationtaskstatus")
        task_status.create(bind, checkfirst=True)
        status_type = task_status
    else:
        status_type = sa.Enum("PENDING", "PROCESSING", "SUCCESS", "FAILED", "REFUNDED", name="generationtaskstatus")

    if not has_table("generation_tasks"):
        op.create_table(
            "generation_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("mode", sa.String(length=20), nullable=False, server_default="text2img"),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("quality", sa.String(length=20), nullable=False, server_default="medium"),
            sa.Column("size", sa.String(length=40), nullable=False, server_default="1024x1024"),
            sa.Column("status", status_type, nullable=False, server_default="PENDING"),
            sa.Column("points_cost", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("image_url", sa.Text(), nullable=True),
            sa.Column("source_image_path", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_generation_tasks_id"), "generation_tasks", ["id"], unique=False)
        op.create_index(op.f("ix_generation_tasks_user_id"), "generation_tasks", ["user_id"], unique=False)
        op.create_index(op.f("ix_generation_tasks_status"), "generation_tasks", ["status"], unique=False)
        op.create_index(op.f("ix_generation_tasks_created_at"), "generation_tasks", ["created_at"], unique=False)
    else:
        if not has_column("generation_tasks", "retry_count"):
            op.add_column("generation_tasks", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        if not has_column("generation_tasks", "max_retries"):
            op.add_column("generation_tasks", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"))
        if not has_column("generation_tasks", "locked_at"):
            op.add_column("generation_tasks", sa.Column("locked_at", sa.DateTime(), nullable=True))
        if not has_index("generation_tasks", op.f("ix_generation_tasks_status")):
            op.create_index(op.f("ix_generation_tasks_status"), "generation_tasks", ["status"], unique=False)
        if not has_index("generation_tasks", op.f("ix_generation_tasks_created_at")):
            op.create_index(op.f("ix_generation_tasks_created_at"), "generation_tasks", ["created_at"], unique=False)

    if has_table("generate_histories") and not has_column("generate_histories", "task_id"):
        op.add_column("generate_histories", sa.Column("task_id", sa.Integer(), nullable=True))
        op.create_index(op.f("ix_generate_histories_task_id"), "generate_histories", ["task_id"], unique=False)
        op.create_foreign_key(
            "fk_generate_histories_task_id_generation_tasks",
            "generate_histories",
            "generation_tasks",
            ["task_id"],
            ["id"],
        )


def downgrade() -> None:
    if has_table("generate_histories") and has_column("generate_histories", "task_id"):
        op.drop_constraint("fk_generate_histories_task_id_generation_tasks", "generate_histories", type_="foreignkey")
        op.drop_index(op.f("ix_generate_histories_task_id"), table_name="generate_histories")
        op.drop_column("generate_histories", "task_id")

    if has_table("generation_tasks"):
        op.drop_index(op.f("ix_generation_tasks_created_at"), table_name="generation_tasks")
        op.drop_index(op.f("ix_generation_tasks_status"), table_name="generation_tasks")
        op.drop_index(op.f("ix_generation_tasks_user_id"), table_name="generation_tasks")
        op.drop_index(op.f("ix_generation_tasks_id"), table_name="generation_tasks")
        op.drop_table("generation_tasks")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="generationtaskstatus").drop(bind, checkfirst=True)
