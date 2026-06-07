from datetime import datetime, timedelta

from sqlalchemy import select, update
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

    FREE_COST_TABLE = {
        "low": 1,
        "medium": 3,
    }

    @staticmethod
    def get_cost(is_member: bool, quality: str) -> int:
        quality = quality.lower()
        if quality not in ("low", "medium", "high"):
            raise ValueError(f"Invalid quality: {quality}")
        return PointManager.COST_TABLE.get((is_member, quality), 3)

    @staticmethod
    async def deduct_points(db: AsyncSession, user_id: int, cost: int) -> bool:
        now = datetime.utcnow()
        # 优先判定免费积分: 仅 low(1分) / medium(3分) 可用
        if cost in (1, 3):
            stmt_free = (
                update(User)
                .where(User.id == user_id, User.free_points >= cost)
                .values(free_points=User.free_points - cost)
            )
            result = await db.execute(stmt_free)
            await db.flush()
            if result.rowcount > 0:
                return True

        # 扣普通积分
        stmt = (
            update(User)
            .where(User.id == user_id, User.points >= cost)
            .values(points=User.points - cost)
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount > 0

    @staticmethod
    async def add_points(db: AsyncSession, user_id: int, amount: int) -> None:
        # 原子递增,避免 read-modify-write 竞态
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(points=User.points + amount)
        )
        await db.execute(stmt)
        await db.flush()

    @staticmethod
    async def activate_membership(
        db: AsyncSession, user_id: int, duration_days: int, points_bonus: int
    ) -> None:
        now = datetime.utcnow()
        # 锁住用户行，避免多笔会员订单并发续期时丢失到期时间更新。
        result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if user is None:
            return

        user.points += points_bonus
        if user.is_member and user.member_expire_at and user.member_expire_at > now:
            user.member_expire_at = user.member_expire_at + timedelta(days=duration_days)
        else:
            user.member_expire_at = now + timedelta(days=duration_days)
        user.is_member = True
        await db.flush()
