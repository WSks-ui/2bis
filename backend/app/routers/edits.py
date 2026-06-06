import traceback
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import MAX_UPLOAD_SIZE
from app.database import get_db
from app.dependencies import get_current_user
from app.models import GenerateHistory, User
from app.services.ai_client import AIClient
from app.services.image_storage import save_data_url
from app.services.point_manager import PointManager

router = APIRouter(prefix="/edits", tags=["edits"])


@router.post("")
async def edit_image(
    image: UploadFile = File(...),
    prompt: str = Form(..., min_length=1, max_length=2000),
    quality: str = Form(default="low"),
    size: str = Form(default="1024x1024"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image file cannot be empty")
    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large (max {MAX_UPLOAD_SIZE // 1024 // 1024}MB)",
        )

    cost = PointManager.get_cost(current_user.is_member, quality)
    deducted = await PointManager.deduct_points(db, current_user.id, cost)
    if not deducted:
        raise HTTPException(status_code=400, detail="Insufficient points")

    print(f"[EDIT] user={current_user.username} prompt={prompt[:50]}... quality={quality} size={size} cost={cost}")

    try:
        raw_data_url = await AIClient.edit(image_bytes, prompt, quality, size, image.filename or "image.png")
    except Exception as e:
        await PointManager.add_points(db, current_user.id, cost)
        await db.flush()
        print(f"[EDIT ERROR] {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI edit failed: {str(e)}")

    image_url = await save_data_url(raw_data_url, current_user.id)
    print(f"[EDIT SUCCESS] image saved -> {image_url}")

    history = GenerateHistory(
        user_id=current_user.id,
        prompt=f"[图生图] {prompt}",
        image_url=image_url,
        quality=quality,
        points_cost=cost,
        created_at=datetime.utcnow(),
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    return {
        "id": history.id,
        "prompt": history.prompt,
        "image_url": history.image_url,
        "quality": history.quality,
        "points_cost": history.points_cost,
        "created_at": history.created_at.isoformat(),
    }
