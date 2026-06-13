from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import GENERATION_MAX_RETRIES, MAX_UPLOAD_SIZE
from app.database import get_db
from app.dependencies import get_current_user
from app.models import GenerationTask, GenerationTaskStatus, User
from app.schemas import GenerationTaskResponse
from app.services.generation_options import GenerationOptions, GenerationOptionsError
from app.services.quota_manager import QuotaError, QuotaManager
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
async def edit_image(
    image: UploadFile = File(...),
    prompt: str = Form(..., min_length=1, max_length=2000),
    quality: str = Form(default="low"),
    size: str = Form(default="1024x1024"),
    workflow_type: str = Form(default="standard", max_length=40),
    workflow_preset: str | None = Form(default=None, max_length=80),
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

    try:
        source_image_mime_type = GenerationOptions.validate_upload_image(image_bytes, image.content_type)
        normalized_quality = GenerationOptions.normalize_quality(quality)
        normalized_size = GenerationOptions.normalize_size(size)
        normalized_workflow = QuotaManager.normalize_workflow_type(workflow_type)
        normalized_workflow_preset = QuotaManager.normalize_workflow_preset(workflow_preset)
        deduction = await QuotaManager.deduct_for_generation(
            db,
            current_user.id,
            normalized_quality,
            normalized_workflow,
        )
    except (GenerationOptionsError, QuotaError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    source_image_path = await save_upload_file(image_bytes, current_user.id, image.filename)
    task = GenerationTask(
        user_id=current_user.id,
        mode="edit",
        prompt=prompt.strip(),
        quality=normalized_quality,
        size=normalized_size,
        points_cost=deduction.cost,
        balance_source=deduction.balance_source,
        workflow_type=deduction.workflow_type,
        workflow_cost=deduction.workflow_cost,
        workflow_preset=normalized_workflow_preset,
        source_image_path=source_image_path,
        source_image_mime_type=source_image_mime_type,
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
