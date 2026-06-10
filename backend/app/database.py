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

        if "generation_tasks" in tables:
            columns = _sqlite_columns(cursor, "generation_tasks")
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
    from app.models import DailyCheckin, GenerateHistory, GenerationTask, Order, User  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
