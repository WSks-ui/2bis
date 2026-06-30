from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL, DB_MAX_OVERFLOW, DB_POOL_RECYCLE, DB_POOL_SIZE


_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"timeout": 30},
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=DB_POOL_RECYCLE,
    )


def _sqlite_columns(cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def _sqlite_add_upstream_audit_columns(cursor, table_name: str, columns: set[str]) -> None:
    audit_columns = {
        "upstream_model": "VARCHAR(80)",
        "upstream_endpoint": "VARCHAR(120)",
        "upstream_request_quality": "VARCHAR(30)",
        "upstream_request_size": "VARCHAR(40)",
        "upstream_response_format": "VARCHAR(30)",
        "upstream_request_id": "VARCHAR(120)",
        "upstream_content_type": "VARCHAR(120)",
        "upstream_elapsed_seconds": "FLOAT",
        "upstream_header_seconds": "FLOAT",
        "upstream_body_seconds": "FLOAT",
        "upstream_parse_seconds": "FLOAT",
        "upstream_save_seconds": "FLOAT",
        "upstream_body_bytes": "INTEGER",
        "upstream_content_length": "INTEGER",
        "upstream_transfer_encoding": "VARCHAR(80)",
        "upstream_payload_length": "INTEGER",
    }
    for column_name, column_type in audit_columns.items():
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def _sqlite_create_studio_tables(cursor, tables: set[str]) -> None:
    # Studio 画布是新能力，但本地 SQLite 可能长期不跑 Alembic；这里负责让旧开发库能原地启动。
    if "workspaces" not in tables:
        cursor.execute(
            """
            CREATE TABLE workspaces (
                id INTEGER NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name VARCHAR(120) NOT NULL,
                description TEXT,
                cover_asset_id INTEGER,
                settings_json TEXT DEFAULT '{}' NOT NULL,
                canvas_revision INTEGER DEFAULT 0 NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                last_opened_at DATETIME,
                archived_at DATETIME,
                deleted_at DATETIME,
                PRIMARY KEY (id)
            )
            """
        )
        cursor.execute("CREATE INDEX ix_workspaces_id ON workspaces (id)")
        cursor.execute("CREATE INDEX ix_workspaces_user_id ON workspaces (user_id)")
        cursor.execute("CREATE INDEX ix_workspaces_archived_at ON workspaces (archived_at)")
        cursor.execute("CREATE INDEX ix_workspaces_deleted_at ON workspaces (deleted_at)")

    if "workspace_assets" not in tables:
        cursor.execute(
            """
            CREATE TABLE workspace_assets (
                id INTEGER NOT NULL,
                workspace_id INTEGER NOT NULL REFERENCES workspaces(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                asset_type VARCHAR(30) DEFAULT 'image' NOT NULL,
                source_type VARCHAR(40) DEFAULT 'upload' NOT NULL,
                title VARCHAR(160),
                url TEXT,
                thumbnail_url TEXT,
                mime_type VARCHAR(80),
                width INTEGER,
                height INTEGER,
                text_content TEXT,
                task_id INTEGER REFERENCES generation_tasks(id),
                history_id INTEGER REFERENCES generate_histories(id),
                parent_asset_id INTEGER REFERENCES workspace_assets(id),
                metadata_json TEXT DEFAULT '{}' NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                deleted_at DATETIME,
                PRIMARY KEY (id)
            )
            """
        )
        cursor.execute("CREATE INDEX ix_workspace_assets_id ON workspace_assets (id)")
        cursor.execute("CREATE INDEX ix_workspace_assets_workspace_id ON workspace_assets (workspace_id)")
        cursor.execute("CREATE INDEX ix_workspace_assets_user_id ON workspace_assets (user_id)")
        cursor.execute("CREATE INDEX ix_workspace_assets_asset_type ON workspace_assets (asset_type)")
        cursor.execute("CREATE INDEX ix_workspace_assets_source_type ON workspace_assets (source_type)")
        cursor.execute("CREATE INDEX ix_workspace_assets_task_id ON workspace_assets (task_id)")
        cursor.execute("CREATE INDEX ix_workspace_assets_history_id ON workspace_assets (history_id)")
        cursor.execute("CREATE INDEX ix_workspace_assets_deleted_at ON workspace_assets (deleted_at)")

    if "canvas_items" not in tables:
        cursor.execute(
            """
            CREATE TABLE canvas_items (
                id INTEGER NOT NULL,
                workspace_id INTEGER NOT NULL REFERENCES workspaces(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                asset_id INTEGER REFERENCES workspace_assets(id),
                task_id INTEGER REFERENCES generation_tasks(id),
                item_type VARCHAR(30) NOT NULL,
                x FLOAT DEFAULT 0 NOT NULL,
                y FLOAT DEFAULT 0 NOT NULL,
                width FLOAT DEFAULT 240 NOT NULL,
                height FLOAT DEFAULT 180 NOT NULL,
                rotation FLOAT DEFAULT 0 NOT NULL,
                z_index INTEGER DEFAULT 0 NOT NULL,
                locked BOOLEAN DEFAULT 0 NOT NULL,
                title VARCHAR(160),
                data_json TEXT DEFAULT '{}' NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                deleted_at DATETIME,
                PRIMARY KEY (id)
            )
            """
        )
        cursor.execute("CREATE INDEX ix_canvas_items_id ON canvas_items (id)")
        cursor.execute("CREATE INDEX ix_canvas_items_workspace_id ON canvas_items (workspace_id)")
        cursor.execute("CREATE INDEX ix_canvas_items_user_id ON canvas_items (user_id)")
        cursor.execute("CREATE INDEX ix_canvas_items_asset_id ON canvas_items (asset_id)")
        cursor.execute("CREATE INDEX ix_canvas_items_task_id ON canvas_items (task_id)")
        cursor.execute("CREATE INDEX ix_canvas_items_item_type ON canvas_items (item_type)")
        cursor.execute("CREATE INDEX ix_canvas_items_deleted_at ON canvas_items (deleted_at)")

    if "canvas_relations" not in tables:
        cursor.execute(
            """
            CREATE TABLE canvas_relations (
                id INTEGER NOT NULL,
                workspace_id INTEGER NOT NULL REFERENCES workspaces(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                source_item_id INTEGER NOT NULL REFERENCES canvas_items(id),
                target_item_id INTEGER NOT NULL REFERENCES canvas_items(id),
                relation_type VARCHAR(40) NOT NULL,
                label VARCHAR(120),
                strength FLOAT DEFAULT 1 NOT NULL,
                data_json TEXT DEFAULT '{}' NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                deleted_at DATETIME,
                PRIMARY KEY (id)
            )
            """
        )
        cursor.execute("CREATE INDEX ix_canvas_relations_id ON canvas_relations (id)")
        cursor.execute("CREATE INDEX ix_canvas_relations_workspace_id ON canvas_relations (workspace_id)")
        cursor.execute("CREATE INDEX ix_canvas_relations_user_id ON canvas_relations (user_id)")
        cursor.execute("CREATE INDEX ix_canvas_relations_source_item_id ON canvas_relations (source_item_id)")
        cursor.execute("CREATE INDEX ix_canvas_relations_target_item_id ON canvas_relations (target_item_id)")
        cursor.execute("CREATE INDEX ix_canvas_relations_relation_type ON canvas_relations (relation_type)")
        cursor.execute("CREATE INDEX ix_canvas_relations_deleted_at ON canvas_relations (deleted_at)")


if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _on_sqlite_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        if "generate_histories" in tables:
            columns = _sqlite_columns(cursor, "generate_histories")
            if "task_id" not in columns:
                cursor.execute(
                    "ALTER TABLE generate_histories ADD COLUMN task_id INTEGER REFERENCES generation_tasks(id)"
                )
            if "balance_source" not in columns:
                cursor.execute("ALTER TABLE generate_histories ADD COLUMN balance_source VARCHAR(20)")
            if "workflow_type" not in columns:
                cursor.execute(
                    "ALTER TABLE generate_histories ADD COLUMN workflow_type VARCHAR(40) DEFAULT 'standard' NOT NULL"
                )
            if "workflow_cost" not in columns:
                cursor.execute("ALTER TABLE generate_histories ADD COLUMN workflow_cost INTEGER DEFAULT 0 NOT NULL")
            if "workflow_preset" not in columns:
                cursor.execute("ALTER TABLE generate_histories ADD COLUMN workflow_preset VARCHAR(80)")
            _sqlite_add_upstream_audit_columns(cursor, "generate_histories", columns)

        if "generation_tasks" in tables:
            columns = _sqlite_columns(cursor, "generation_tasks")
            if "workspace_id" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN workspace_id INTEGER")
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_generation_tasks_workspace_id ON generation_tasks (workspace_id)")
            if "canvas_item_id" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN canvas_item_id INTEGER")
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_generation_tasks_canvas_item_id ON generation_tasks (canvas_item_id)")
            if "balance_source" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN balance_source VARCHAR(20)")
            if "workflow_type" not in columns:
                cursor.execute(
                    "ALTER TABLE generation_tasks ADD COLUMN workflow_type VARCHAR(40) DEFAULT 'standard' NOT NULL"
                )
            if "workflow_cost" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN workflow_cost INTEGER DEFAULT 0 NOT NULL")
            if "workflow_preset" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN workflow_preset VARCHAR(80)")
            if "source_image_mime_type" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN source_image_mime_type VARCHAR(50)")
            if "source_image_paths" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN source_image_paths TEXT")
            if "source_image_mime_types" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN source_image_mime_types TEXT")
            if "source_mask_path" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN source_mask_path TEXT")
            if "source_mask_mime_type" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN source_mask_mime_type VARCHAR(50)")
            if "studio_source_item_ids_json" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN studio_source_item_ids_json TEXT")
            if "progress_stage" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN progress_stage VARCHAR(40)")
            if "progress_message" not in columns:
                cursor.execute("ALTER TABLE generation_tasks ADD COLUMN progress_message TEXT")
            _sqlite_add_upstream_audit_columns(cursor, "generation_tasks", columns)

        if "orders" in tables:
            columns = _sqlite_columns(cursor, "orders")
            if "plan_period" not in columns:
                cursor.execute("ALTER TABLE orders ADD COLUMN plan_period VARCHAR(20)")

        if "users" in tables:
            columns = _sqlite_columns(cursor, "users")
            if "free_points" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN free_points INTEGER DEFAULT 0")
            if "free_points_expire_at" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN free_points_expire_at DATETIME")
            if "last_checkin_date" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN last_checkin_date DATE")
            if "consecutive_days" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN consecutive_days INTEGER DEFAULT 0")
            if "subscription_plan" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN subscription_plan VARCHAR(30)")
            if "subscription_period" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN subscription_period VARCHAR(20)")
            if "monthly_quota_total" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN monthly_quota_total INTEGER DEFAULT 0")
            if "monthly_quota_remaining" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN monthly_quota_remaining INTEGER DEFAULT 0")
            if "monthly_quota_reset_at" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN monthly_quota_reset_at DATETIME")
            if "trial_activated" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN trial_activated BOOLEAN DEFAULT 0")
            if "trial_expire_at" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN trial_expire_at DATETIME")
            if "trial_high_quality_used" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN trial_high_quality_used INTEGER DEFAULT 0")
            if "is_admin" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL")

        if "api_key_configs" not in tables:
            cursor.execute(
                """
                CREATE TABLE api_key_configs (
                    id INTEGER NOT NULL,
                    name VARCHAR(80) NOT NULL,
                    provider VARCHAR(40) NOT NULL,
                    api_url VARCHAR(255) NOT NULL,
                    encrypted_api_key TEXT NOT NULL,
                    key_mask VARCHAR(80) NOT NULL,
                    response_format VARCHAR(30),
                    send_quality BOOLEAN DEFAULT 1 NOT NULL,
                    is_active BOOLEAN DEFAULT 0 NOT NULL,
                    is_enabled BOOLEAN DEFAULT 1 NOT NULL,
                    circuit_state VARCHAR(20) DEFAULT 'closed' NOT NULL,
                    circuit_reason TEXT,
                    circuit_open_until DATETIME,
                    failure_count INTEGER DEFAULT 0 NOT NULL,
                    last_failure_at DATETIME,
                    last_test_status VARCHAR(20),
                    last_test_message TEXT,
                    last_tested_at DATETIME,
                    last_used_at DATETIME,
                    created_by INTEGER REFERENCES users(id),
                    updated_by INTEGER REFERENCES users(id),
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    PRIMARY KEY (id)
                )
                """
            )
            cursor.execute("CREATE INDEX ix_api_key_configs_id ON api_key_configs (id)")
            cursor.execute("CREATE INDEX ix_api_key_configs_is_active ON api_key_configs (is_active)")
            cursor.execute("CREATE INDEX ix_api_key_configs_is_enabled ON api_key_configs (is_enabled)")
        else:
            columns = _sqlite_columns(cursor, "api_key_configs")
            if "circuit_state" not in columns:
                cursor.execute("ALTER TABLE api_key_configs ADD COLUMN circuit_state VARCHAR(20) DEFAULT 'closed' NOT NULL")
            if "send_quality" not in columns:
                cursor.execute("ALTER TABLE api_key_configs ADD COLUMN send_quality BOOLEAN DEFAULT 1 NOT NULL")
            if "circuit_reason" not in columns:
                cursor.execute("ALTER TABLE api_key_configs ADD COLUMN circuit_reason TEXT")
            if "circuit_open_until" not in columns:
                cursor.execute("ALTER TABLE api_key_configs ADD COLUMN circuit_open_until DATETIME")
            if "failure_count" not in columns:
                cursor.execute("ALTER TABLE api_key_configs ADD COLUMN failure_count INTEGER DEFAULT 0 NOT NULL")
            if "last_failure_at" not in columns:
                cursor.execute("ALTER TABLE api_key_configs ADD COLUMN last_failure_at DATETIME")

        if "admin_audit_logs" not in tables:
            cursor.execute(
                """
                CREATE TABLE admin_audit_logs (
                    id INTEGER NOT NULL,
                    admin_user_id INTEGER REFERENCES users(id),
                    action VARCHAR(80) NOT NULL,
                    target_type VARCHAR(60) NOT NULL,
                    target_id INTEGER,
                    summary TEXT,
                    created_at DATETIME NOT NULL,
                    PRIMARY KEY (id)
                )
                """
            )
            cursor.execute("CREATE INDEX ix_admin_audit_logs_id ON admin_audit_logs (id)")
            cursor.execute("CREATE INDEX ix_admin_audit_logs_admin_user_id ON admin_audit_logs (admin_user_id)")
            cursor.execute("CREATE INDEX ix_admin_audit_logs_action ON admin_audit_logs (action)")
            cursor.execute("CREATE INDEX ix_admin_audit_logs_created_at ON admin_audit_logs (created_at)")

        _sqlite_create_studio_tables(cursor, tables)
        cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    from app.models import (  # noqa: F401
        AdminAuditLog,
        ApiKeyConfig,
        CanvasItem,
        CanvasRelation,
        DailyCheckin,
        GenerateHistory,
        GenerationTask,
        Order,
        User,
        Workspace,
        WorkspaceAsset,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
