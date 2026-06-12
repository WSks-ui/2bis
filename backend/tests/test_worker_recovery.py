import unittest
from datetime import datetime, timedelta
from types import ModuleType
from unittest.mock import patch
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.modules.setdefault("boto3", ModuleType("boto3"))
redis_module = sys.modules.setdefault("redis", ModuleType("redis"))
redis_asyncio_module = sys.modules.setdefault("redis.asyncio", ModuleType("redis.asyncio"))
setattr(redis_asyncio_module, "Redis", object)
setattr(redis_module, "asyncio", redis_asyncio_module)
import worker
from app.database import Base
from app.models import GenerationTask, GenerationTaskStatus, User


class WorkerRecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session_patch = patch.object(worker, "async_session", self.session_factory)
        self.session_patch.start()

    async def asyncTearDown(self) -> None:
        self.session_patch.stop()
        await self.engine.dispose()

    async def test_stale_processing_task_is_refunded_without_requeue(self) -> None:
        async with self.session_factory() as db:
            user = User(
                username="stale-user",
                hashed_password="x",
                monthly_quota_total=10,
                monthly_quota_remaining=7,
            )
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                status=GenerationTaskStatus.PROCESSING,
                points_cost=3,
                balance_source="quota",
                locked_at=datetime.utcnow() - timedelta(hours=2),
                retry_count=2,
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with patch.object(worker, "enqueue_generation_task", autospec=True) as enqueue:
            await worker.recover_stale_processing_tasks()

        enqueue.assert_not_called()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.REFUNDED)
        self.assertIsNone(task.locked_at)
        self.assertIsNotNone(task.finished_at)
        self.assertIn("quota has been refunded", task.error_message)
        self.assertEqual(user.monthly_quota_remaining, 10)


if __name__ == "__main__":
    unittest.main()
