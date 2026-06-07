from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL, DB_MAX_OVERFLOW, DB_POOL_RECYCLE, DB_POOL_SIZE

# 根据 DATABASE_URL 前缀自动选择引擎配置: 开发用 SQLite, 生产用 PostgreSQL
_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"timeout": 30},
    )
else:
    # PostgreSQL: 配置连接池,应对数百并发
    # pool_size 基线连接, max_overflow 突发容量, pool_pre_ping 防止连接被服务端关闭后误用
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=DB_POOL_RECYCLE,
    )


if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _on_sqlite_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        # 自动迁移: 给旧数据库补缺失列
        cursor.execute("PRAGMA table_info(generate_histories)")
        columns = {row[1] for row in cursor.fetchall()}
        if "task_id" not in columns:
            cursor.execute(
                "ALTER TABLE generate_histories ADD COLUMN task_id INTEGER REFERENCES generation_tasks(id)"
            )
        cursor.execute("PRAGMA table_info(users)")
        user_columns = {row[1] for row in cursor.fetchall()}
        if "free_points" not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN free_points INTEGER DEFAULT 0")
        if "free_points_expire_at" not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN free_points_expire_at DATETIME")
        if "last_checkin_date" not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN last_checkin_date DATE")
        if "consecutive_days" not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN consecutive_days INTEGER DEFAULT 0")
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
