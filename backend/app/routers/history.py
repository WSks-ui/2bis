from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import GenerateHistory, User
from app.schemas import HistoryItem

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryItem])
async def list_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GenerateHistory)
        .where(GenerateHistory.user_id == current_user.id)
        .order_by(GenerateHistory.created_at.desc())
        .limit(50)
    )
    histories = result.scalars().all()
    return [
        HistoryItem(
            id=h.id,
            prompt=h.prompt,
            image_url=h.image_url,
            quality=h.quality,
            points_cost=h.points_cost,
            created_at=h.created_at,
        )
        for h in histories
    ]
