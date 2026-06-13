import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.config import GENERATION_MAX_RETRIES
from app.models import GenerationTask, GenerationTaskStatus, User
from app.schemas import GenerateRequest, GenerationTaskResponse
from app.services.generation_options import GenerationOptions, GenerationOptionsError
from app.services.quota_manager import QuotaError, QuotaManager
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
        balance_source=task.balance_source,
        workflow_type=task.workflow_type,
        workflow_cost=task.workflow_cost,
        workflow_preset=task.workflow_preset,
        upstream_model=task.upstream_model,
        upstream_endpoint=task.upstream_endpoint,
        upstream_request_quality=task.upstream_request_quality,
        upstream_request_size=task.upstream_request_size,
        upstream_response_format=task.upstream_response_format,
        upstream_request_id=task.upstream_request_id,
        upstream_content_type=task.upstream_content_type,
        upstream_elapsed_seconds=task.upstream_elapsed_seconds,
        upstream_payload_length=task.upstream_payload_length,
        progress_stage=task.progress_stage,
        progress_message=task.progress_message,
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

    try:
        quality = GenerationOptions.normalize_quality(data.quality)
        size = GenerationOptions.normalize_size(data.size)
        workflow_type = QuotaManager.normalize_workflow_type(data.workflow_type)
        workflow_preset = QuotaManager.normalize_workflow_preset(data.workflow_preset)
    except (GenerationOptionsError, QuotaError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        deduction = await QuotaManager.deduct_for_generation(
            db,
            current_user.id,
            quality,
            workflow_type,
        )
    except QuotaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task = GenerationTask(
        user_id=current_user.id,
        mode="text2img",
        prompt=data.prompt.strip(),
        quality=quality,
        size=size,
        points_cost=deduction.cost,
        balance_source=deduction.balance_source,
        workflow_type=deduction.workflow_type,
        workflow_cost=deduction.workflow_cost,
        workflow_preset=workflow_preset,
        max_retries=GENERATION_MAX_RETRIES,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    try:
        await enqueue_generation_task(task.id)
    except Exception as e:
        await QuotaManager.refund_generation(
            db, current_user.id, task.points_cost, task.balance_source
        )
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
