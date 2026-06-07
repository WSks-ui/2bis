import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.config import GENERATION_MAX_RETRIES
from app.models import GenerationTask, GenerationTaskStatus, User
from app.schemas import GenerateRequest, GenerationTaskResponse
from app.services.point_manager import PointManager
from app.services.task_queue import enqueue_generation_task

router = APIRouter(prefix="/generate", tags=["generate"])


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

    task = GenerationTask(
        user_id=current_user.id,
        mode="text2img",
        prompt=data.prompt.strip(),
        quality=data.quality,
        size=data.size,
        points_cost=cost,
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


@router.get("/tasks", response_model=list[GenerationTaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GenerationTask)
        .where(GenerationTask.user_id == current_user.id)
        .order_by(GenerationTask.created_at.desc())
        .limit(50)
    )
    return [task_response(task) for task in result.scalars().all()]


@router.get("/tasks/{task_id}", response_model=GenerationTaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GenerationTask).where(
            GenerationTask.id == task_id,
            GenerationTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_response(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GenerationTask).where(
            GenerationTask.id == task_id,
            GenerationTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    image_url = task.image_url
    await db.delete(task)
    await db.commit()

    if image_url and image_url.startswith("/static/"):
        try:
            file_path = image_url[len("/"):]
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
