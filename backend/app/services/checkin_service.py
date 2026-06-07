from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import CHECKIN_REWARDS, FREE_POINTS_TTL_DAYS
from app.models import DailyCheckin, User


def _calculate_checkin(user: User, today: date) -> tuple[int, int, int, int]:
    """返回 (day_number, reward, free_points, expire_seconds).

    连续签到周期 7 天: 第 1-7 天分别奖励,第 8 天回到第 1 天.
    奖励规则: 1→1, 2→1, 3→1, 4→2, 5→1, 6→1, 7→3
    """
    consecutive = user.consecutive_days
    if user.last_checkin_date is None:
        day_number = 1
    else:
        delta = (today - user.last_checkin_date).days
        if delta == 1:
            day_number = consecutive + 1
        else:
            day_number = 1

    if day_number > 7:
        day_number = 1

    reward = CHECKIN_REWARDS.get(day_number, 1)
    expire_at = datetime.utcnow() + timedelta(days=FREE_POINTS_TTL_DAYS)
    return day_number, reward, user.free_points + reward, expire_at


async def perform_checkin(user: User, db: AsyncSession) -> dict:
    today = date.today()

    day_number, reward, new_free_points, expire_at = _calculate_checkin(user, today)

    record = DailyCheckin(
        user_id=user.id,
        checkin_date=today,
        day_number=day_number,
        reward=reward,
    )
    db.add(record)

    user.free_points = new_free_points
    user.free_points_expire_at = expire_at
    user.consecutive_days = day_number
    user.last_checkin_date = today
    await db.commit()
    await db.refresh(user)

    return {
        "day_number": day_number,
        "reward": reward,
        "free_points": user.free_points,
        "free_points_expire_at": expire_at,
        "consecutive_days": day_number,
    }


def checkin_status(user: User) -> dict:
    today = date.today()
    available = user.last_checkin_date is None or user.last_checkin_date < today
    day_number, reward, free_points, expire_at = _calculate_checkin(user, today)
    return {
        "checkin_available": available,
        "consecutive_days": user.consecutive_days,
        "day_number": day_number,
        "reward": reward,
        "free_points": user.free_points,
        "free_points_expire_at": user.free_points_expire_at,
        "bonus_rule": ", ".join(f"D{day}:{points}" for day, points in sorted(CHECKIN_REWARDS.items())),
    }
