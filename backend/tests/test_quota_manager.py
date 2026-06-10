import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import User
from app.services.quota_manager import (
    BALANCE_SOURCE_FREE_POINTS,
    BALANCE_SOURCE_QUOTA,
    QuotaError,
    QuotaManager,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class QuotaManagerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def create_user(self, **kwargs) -> int:
        defaults = {
            "username": f"user-{utcnow().timestamp()}",
            "hashed_password": "x",
            "points": 0,
            "free_points": 0,
            "is_member": False,
            "monthly_quota_total": 0,
            "monthly_quota_remaining": 0,
            "trial_activated": False,
            "trial_high_quality_used": 0,
        }
        defaults.update(kwargs)
        async with self.session_factory() as db:
            user = User(**defaults)
            db.add(user)
            await db.commit()
            return user.id

    async def get_user(self, user_id: int) -> User:
        async with self.session_factory() as db:
            return await db.get(User, user_id)

    async def test_standard_low_uses_experience_points_first(self) -> None:
        user_id = await self.create_user(
            free_points=3,
            free_points_expire_at=utcnow() + timedelta(days=1),
            subscription_plan="light",
            subscription_period="monthly",
            member_expire_at=utcnow() + timedelta(days=30),
            monthly_quota_total=100,
            monthly_quota_remaining=50,
            monthly_quota_reset_at=utcnow() + timedelta(days=30),
        )

        async with self.session_factory() as db:
            result = await QuotaManager.deduct_for_generation(db, user_id, "low")
            await db.commit()

        user = await self.get_user(user_id)
        self.assertEqual(result.balance_source, BALANCE_SOURCE_FREE_POINTS)
        self.assertEqual(result.workflow_type, "standard")
        self.assertEqual(result.workflow_cost, 1)
        self.assertEqual(user.free_points, 2)
        self.assertEqual(user.monthly_quota_remaining, 50)

    async def test_high_quality_uses_subscription_quota(self) -> None:
        user_id = await self.create_user(
            free_points=10,
            free_points_expire_at=utcnow() + timedelta(days=1),
            subscription_plan="creator",
            subscription_period="monthly",
            member_expire_at=utcnow() + timedelta(days=30),
            monthly_quota_total=350,
            monthly_quota_remaining=20,
            monthly_quota_reset_at=utcnow() + timedelta(days=30),
        )

        async with self.session_factory() as db:
            result = await QuotaManager.deduct_for_generation(db, user_id, "high")
            await db.commit()

        user = await self.get_user(user_id)
        self.assertEqual(result.balance_source, BALANCE_SOURCE_QUOTA)
        self.assertEqual(result.workflow_cost, 3)
        self.assertEqual(user.free_points, 10)
        self.assertEqual(user.monthly_quota_remaining, 17)

    async def test_professional_workflow_uses_quota_not_experience_points(self) -> None:
        user_id = await self.create_user(
            free_points=10,
            free_points_expire_at=utcnow() + timedelta(days=1),
            subscription_plan="pro",
            subscription_period="monthly",
            member_expire_at=utcnow() + timedelta(days=30),
            monthly_quota_total=800,
            monthly_quota_remaining=100,
            monthly_quota_reset_at=utcnow() + timedelta(days=30),
        )

        async with self.session_factory() as db:
            result = await QuotaManager.deduct_for_generation(db, user_id, "low", "professional")
            await QuotaManager.refund_generation(db, user_id, result.cost, result.balance_source)
            await db.commit()

        user = await self.get_user(user_id)
        self.assertEqual(result.balance_source, BALANCE_SOURCE_QUOTA)
        self.assertEqual(result.workflow_type, "professional")
        self.assertEqual(result.workflow_cost, 1)
        self.assertEqual(user.free_points, 10)
        self.assertEqual(user.monthly_quota_remaining, 100)

    async def test_unknown_workflow_is_rejected(self) -> None:
        user_id = await self.create_user()

        async with self.session_factory() as db:
            with self.assertRaises(QuotaError):
                await QuotaManager.deduct_for_generation(db, user_id, "low", "unknown")


if __name__ == "__main__":
    unittest.main()
