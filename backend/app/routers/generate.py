from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import traceback

from app.database import get_db
from app.dependencies import get_current_user
from app.models import GenerateHistory, User
from app.schemas import GenerateRequest, GenerateResponse
from app.services.ai_client import AIClient
from app.services.point_manager import PointManager

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=GenerateResponse)
async def generate(
    data: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not data.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    cost = PointManager.get_cost(current_user.is_member, data.quality)
    deducted = await PointManager.deduct_points(db, current_user.id, cost)
    if not deducted:
        raise HTTPException(status_code=400, detail="Insufficient points")

    print(f"[GENERATE] user={current_user.username} prompt={data.prompt[:50]}... quality={data.quality} cost={cost}")

    try:
        image_url = await AIClient.generate(data.prompt, data.quality, data.size)
    except Exception as e:
        await PointManager.add_points(db, current_user.id, cost)
        await db.flush()
        print(f"[GENERATE ERROR] {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    print(f"[GENERATE SUCCESS] image_url length={len(image_url)}")

    history = GenerateHistory(
        user_id=current_user.id,
        prompt=data.prompt,
        image_url=image_url,
        quality=data.quality,
        points_cost=cost,
        created_at=datetime.utcnow(),
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    return GenerateResponse(
        id=history.id,
        prompt=history.prompt,
        image_url=history.image_url,
        quality=history.quality,
        points_cost=history.points_cost,
        created_at=history.created_at,
    )
