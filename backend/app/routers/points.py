from datetime import datetime, timedelta

from fastapi import APIRouter, Depends

from app.config import FREE_POINTS_TTL_DAYS
from app.dependencies import get_current_user
from app.models import User
from app.schemas import PointsBalanceResponse, PointsPack
from app.services.payment_simulator import PaymentSimulator

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/packs", response_model=list[PointsPack])
async def list_packs():
    return [PointsPack(**p) for p in PaymentSimulator.POINTS_PACKS]


@router.get("/balance", response_model=PointsBalanceResponse)
async def get_balance(current_user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    if current_user.free_points_expire_at and current_user.free_points_expire_at < now:
        current_user.free_points = 0
        current_user.free_points_expire_at = now + timedelta(days=FREE_POINTS_TTL_DAYS)

    return PointsBalanceResponse(
        username=current_user.username,
        points=current_user.points,
        free_points=current_user.free_points,
        free_points_expire_at=current_user.free_points_expire_at,
        is_member=current_user.is_member,
        member_expire_at=current_user.member_expire_at,
    )
