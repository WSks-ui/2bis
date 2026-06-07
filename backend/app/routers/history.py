import os

from fastapi import APIRouter, Depends, HTTPException
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
            task_id=h.task_id,
            prompt=h.prompt,
            image_url=h.image_url,
            quality=h.quality,
            points_cost=h.points_cost,
            created_at=h.created_at,
        )
        for h in histories
    ]


@router.delete("/{history_id}", status_code=204)
async def delete_history(
    history_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GenerateHistory).where(
            GenerateHistory.id == history_id,
            GenerateHistory.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="History not found")

    image_url = record.image_url
    await db.delete(record)
    await db.commit()

    if image_url and image_url.startswith("/static/"):
        try:
            file_path = image_url[len("/"):]
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
