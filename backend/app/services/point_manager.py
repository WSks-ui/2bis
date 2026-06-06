from datetime import datetime, timedelta

from sqlalchemy import update
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
        # 原子 SQL：WHERE 子句 + UPDATE 在单条语句内完成,杜绝并发 TOCTOU 竞态
        # 仅当用户存在且积分充足时才扣减成功 (rowcount=1);否则 rowcount=0
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
        # 原子递增积分
        stmt_points = (
            update(User)
            .where(User.id == user_id)
            .values(points=User.points + points_bonus)
        )
        await db.execute(stmt_points)

        # 会员到期时间: 用 CASE 判断是否续期
        # 如果当前是有效会员 → 在原到期时间上续期;否则从 now 开始
        from sqlalchemy import case, select

        # 先查出当前到期时间,再决定续期逻辑
        result = await db.execute(select(User.is_member, User.member_expire_at).where(User.id == user_id))
        row = result.first()
        if row is None:
            return

        is_member, expire_at = row
        if is_member and expire_at and expire_at > now:
            new_expire = expire_at + timedelta(days=duration_days)
        else:
            new_expire = now + timedelta(days=duration_days)

        stmt_member = (
            update(User)
            .where(User.id == user_id)
            .values(is_member=True, member_expire_at=new_expire)
        )
        await db.execute(stmt_member)
        await db.flush()
