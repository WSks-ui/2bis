import os
import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import GenerateHistory, User
from app.schemas import HistoryItem, HistoryPageResponse
from app.services.image_derivatives import delete_thumbnail, ensure_thumbnail

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryPageResponse)
async def list_history(
    page: int = 1,
    page_size: int = 12,
    range: str = "all",
    workflow: str = "all",
    quality: str = "all",
    source: str = "all",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 24)
    conditions = [GenerateHistory.user_id == current_user.id]
    if workflow != "all":
        conditions.append(GenerateHistory.workflow_type == workflow)
    if quality != "all":
        conditions.append(GenerateHistory.quality == quality)
    if source != "all":
        conditions.append(GenerateHistory.balance_source == source)
    since = history_since(range)
    if since is not None:
        conditions.append(GenerateHistory.created_at >= since)

    total_result = await db.execute(
        select(func.count()).select_from(GenerateHistory).where(*conditions)
    )
    total = int(total_result.scalar_one() or 0)

    result = await db.execute(
        select(GenerateHistory)
        .where(*conditions)
        .order_by(GenerateHistory.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    histories = result.scalars().all()
    records = []
    for h in histories:
        thumbnail_url = await ensure_thumbnail(h.image_url)
        records.append(
            HistoryItem(
                id=h.id,
                task_id=h.task_id,
                prompt=h.prompt,
                image_url=h.image_url,
                thumbnail_url=thumbnail_url,
                quality=h.quality,
                points_cost=h.points_cost,
                balance_source=h.balance_source,
                workflow_type=h.workflow_type,
                workflow_cost=h.workflow_cost,
                workflow_preset=h.workflow_preset,
                upstream_model=h.upstream_model,
                upstream_endpoint=h.upstream_endpoint,
                upstream_request_quality=h.upstream_request_quality,
                upstream_request_size=h.upstream_request_size,
                upstream_response_format=h.upstream_response_format,
                upstream_request_id=h.upstream_request_id,
                upstream_content_type=h.upstream_content_type,
                upstream_elapsed_seconds=h.upstream_elapsed_seconds,
                upstream_payload_length=h.upstream_payload_length,
                created_at=h.created_at,
            )
        )

    return HistoryPageResponse(
        records=records,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)) if total else 1,
    )


def history_since(range_value: str) -> datetime | None:
    now = datetime.utcnow()
    if range_value == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if range_value == "week":
        return now - timedelta(days=7)
    if range_value == "month":
        return now - timedelta(days=30)
    return None


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
            await delete_thumbnail(image_url)
            file_path = image_url[len("/"):]
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
