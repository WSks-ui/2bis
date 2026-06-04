from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class PointManager:
    COST_TABLE = {
        (False, "low"): 1,
        (False, "medium"): 3,
        (False, "high"): 5,
        (True, "low"): 1,
        (True, "medium"): 2,
        (True, "high"): 3,
    }

    @staticmethod
    def get_cost(is_member: bool, quality: str) -> int:
        quality = quality.lower()
        if quality not in ("low", "medium", "high"):
            raise ValueError(f"Invalid quality: {quality}")
        return PointManager.COST_TABLE.get((is_member, quality), 3)

    @staticmethod
    async def deduct_points(db: AsyncSession, user_id: int, cost: int) -> bool:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return False
        if user.points < cost:
            return False
        user.points -= cost
        await db.flush()
        return True

    @staticmethod
    async def add_points(db: AsyncSession, user_id: int, amount: int) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return
        user.points += amount
        await db.flush()

    @staticmethod
    async def activate_membership(
        db: AsyncSession, user_id: int, duration_days: int, points_bonus: int
    ) -> None:
        from datetime import datetime, timedelta

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return
        now = datetime.utcnow()
        if user.is_member and user.member_expire_at and user.member_expire_at > now:
            user.member_expire_at = user.member_expire_at + timedelta(days=duration_days)
        else:
            user.is_member = True
            user.member_expire_at = now + timedelta(days=duration_days)
        user.points += points_bonus
        await db.flush()
