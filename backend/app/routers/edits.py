from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import GENERATION_MAX_RETRIES, MAX_UPLOAD_SIZE
from app.database import get_db
from app.dependencies import get_current_user
from app.models import GenerationTask, GenerationTaskStatus, User
from app.schemas import GenerationTaskResponse
from app.services.point_manager import PointManager
from app.services.task_queue import enqueue_generation_task
from app.services.upload_storage import save_upload_file

router = APIRouter(prefix="/edits", tags=["edits"])


def task_response(task: GenerationTask) -> GenerationTaskResponse:
    return GenerationTaskResponse(
        id=task.id,
        mode=task.mode,
        prompt=task.prompt,
        quality=task.quality,
        size=task.size,
        status=task.status.value,
        points_cost=task.points_cost,
        image_url=task.image_url,
        error_message=task.error_message,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


@router.post("", response_model=GenerationTaskResponse)
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

    source_image_path = await save_upload_file(image_bytes, current_user.id, image.filename)
    task = GenerationTask(
        user_id=current_user.id,
        mode="edit",
        prompt=prompt.strip(),
        quality=quality,
        size=size,
        points_cost=cost,
        source_image_path=source_image_path,
        max_retries=GENERATION_MAX_RETRIES,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    try:
        await enqueue_generation_task(task.id)
    except Exception as e:
        await PointManager.add_points(db, current_user.id, cost)
        task.status = GenerationTaskStatus.REFUNDED
        task.error_message = f"Task queue unavailable: {e}"
        await db.commit()
        raise HTTPException(status_code=503, detail="任务队列暂不可用，请稍后重试")

    return task_response(task)
