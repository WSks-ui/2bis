from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

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
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
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
    from app.models import User, GenerateHistory, Order  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
