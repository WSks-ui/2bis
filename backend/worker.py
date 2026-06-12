import asyncio
import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import or_, select

from app.config import (
    GENERATION_MAX_RETRIES,
    GENERATION_PROCESSING_RECOVERY_SECONDS,
    GENERATION_TASK_TIMEOUT,
    GENERATION_WORKER_CONCURRENCY,
)
from app.database import async_session
from app.models import GenerateHistory, GenerationTask, GenerationTaskStatus
from app.services.ai_client import AIClient, AIImageResult, AIResponsePayloadError, AITimeoutError, close_client
from app.services.generation_options import GenerationOptions
from app.services.image_storage import save_data_url
from app.services.quota_manager import QuotaManager
from app.services.task_queue import close_redis, dequeue_generation_task, enqueue_generation_task
from app.services.upload_storage import read_upload_file

logger = logging.getLogger("generation_worker")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")


def apply_upstream_audit(target, result: AIImageResult) -> None:
    target.upstream_model = result.model
    target.upstream_endpoint = result.endpoint
    target.upstream_request_quality = result.request_quality
    target.upstream_request_size = result.request_size
    target.upstream_response_format = result.request_response_format
    target.upstream_request_id = result.response_request_id
    target.upstream_content_type = result.response_content_type
    target.upstream_elapsed_seconds = round(result.elapsed_seconds, 3)
    target.upstream_payload_length = result.payload_length


async def recover_stale_processing_tasks() -> None:
    cutoff = datetime.utcnow() - timedelta(seconds=GENERATION_PROCESSING_RECOVERY_SECONDS)
    async with async_session() as db:
        result = await db.execute(
            select(GenerationTask).where(
                GenerationTask.status == GenerationTaskStatus.PROCESSING,
                or_(GenerationTask.locked_at.is_(None), GenerationTask.locked_at < cutoff),
            )
        )
        tasks = result.scalars().all()
        for task in tasks:
            await QuotaManager.refund_generation(
                db, task.user_id, task.points_cost, task.balance_source
            )
            task.status = GenerationTaskStatus.REFUNDED
            task.error_message = (
                "Generation worker stopped before receiving the image result; "
                "quota has been refunded to avoid duplicate upstream billing."
            )
            task.locked_at = None
            task.finished_at = datetime.utcnow()
        await db.commit()
        if tasks:
            logger.warning("refunded %s stale processing tasks", len(tasks))


async def process_task(task_id: int) -> None:
    async with async_session() as db:
        result = await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))
        task = result.scalar_one_or_none()
        if task is None or task.status not in {GenerationTaskStatus.PENDING, GenerationTaskStatus.PROCESSING}:
            return

        task.status = GenerationTaskStatus.PROCESSING
        task.started_at = task.started_at or datetime.utcnow()
        task.locked_at = datetime.utcnow()
        task.max_retries = task.max_retries or GENERATION_MAX_RETRIES
        await db.commit()

    try:
        task_started_at = time.monotonic()
        async with async_session() as db:
            result = await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

        logger.info(
            "task %s upstream request started mode=%s quality=%s size=%s",
            task_id,
            task.mode,
            task.quality,
            task.size,
        )
        upstream_started_at = time.monotonic()
        if task.mode == "text2img":
            ai_result = await asyncio.wait_for(
                AIClient.generate_with_metadata(task.prompt, task.quality, task.size),
                timeout=GENERATION_TASK_TIMEOUT,
            )
        else:
            image_bytes = await read_upload_file(task.source_image_path)
            source_mime_type = task.source_image_mime_type or "image/png"
            source_filename = f"image.{GenerationOptions.extension_for_mime(source_mime_type)}"
            ai_result = await asyncio.wait_for(
                AIClient.edit_with_metadata(
                    image_bytes,
                    task.prompt,
                    task.quality,
                    task.size,
                    source_filename,
                    source_mime_type,
                ),
                timeout=GENERATION_TASK_TIMEOUT,
            )
        raw_data_url = ai_result.data_url
        upstream_seconds = time.monotonic() - upstream_started_at
        logger.info(
            "task %s upstream response received in %.1fs, request_quality=%s, request_id=%s, payload length=%s",
            task_id,
            upstream_seconds,
            ai_result.request_quality,
            ai_result.response_request_id,
            len(raw_data_url) if raw_data_url else 0,
        )

        save_started_at = time.monotonic()
        image_url = await save_data_url(raw_data_url, task.user_id)
        save_seconds = time.monotonic() - save_started_at
        logger.info("task %s image saved in %.1fs: %s", task_id, save_seconds, image_url)

        async with async_session() as db:
            result = await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

            task.status = GenerationTaskStatus.SUCCESS
            task.image_url = image_url
            task.error_message = None
            task.locked_at = None
            task.finished_at = datetime.utcnow()
            apply_upstream_audit(task, ai_result)
            history_prompt = f"[图生图] {task.prompt}" if task.mode != "text2img" else task.prompt
            history = GenerateHistory(
                user_id=task.user_id,
                task_id=task.id,
                prompt=history_prompt,
                image_url=image_url,
                quality=task.quality,
                points_cost=task.points_cost,
                balance_source=task.balance_source,
                workflow_type=task.workflow_type,
                workflow_cost=task.workflow_cost,
                workflow_preset=task.workflow_preset,
                created_at=task.finished_at,
            )
            apply_upstream_audit(history, ai_result)
            db.add(history)
            await db.commit()
            total_seconds = time.monotonic() - task_started_at
            logger.info("task %s success in %.1fs", task_id, total_seconds)
    except Exception as e:
        async with async_session() as db:
            result = await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

            task.retry_count += 1
            task.error_message = str(e)
            task.locked_at = None

            can_retry = not isinstance(e, (AIResponsePayloadError, AITimeoutError)) and task.retry_count <= task.max_retries
            if can_retry:
                task.status = GenerationTaskStatus.PENDING
                await db.commit()
                await enqueue_generation_task(task.id)
                logger.exception("task %s failed, retry %s/%s", task_id, task.retry_count, task.max_retries)
                return

            await QuotaManager.refund_generation(
                db, task.user_id, task.points_cost, task.balance_source
            )
            task.status = GenerationTaskStatus.REFUNDED
            task.finished_at = datetime.utcnow()
            await db.commit()
            logger.exception("task %s failed and refunded", task_id)


async def run_with_semaphore(semaphore: asyncio.Semaphore, task_id: int) -> None:
    try:
        await process_task(task_id)
    finally:
        semaphore.release()


async def recovery_loop() -> None:
    while True:
        try:
            await recover_stale_processing_tasks()
        except Exception:
            logger.exception("processing task recovery failed")
        await asyncio.sleep(60)


async def main() -> None:
    await recover_stale_processing_tasks()
    asyncio.create_task(recovery_loop())
    semaphore = asyncio.Semaphore(GENERATION_WORKER_CONCURRENCY)
    running: set[asyncio.Task] = set()
    logger.info("generation worker started, concurrency=%s", GENERATION_WORKER_CONCURRENCY)

    try:
        while True:
            await semaphore.acquire()
            task_id = await dequeue_generation_task(timeout=5)
            if task_id is None:
                semaphore.release()
                continue
            task = asyncio.create_task(run_with_semaphore(semaphore, task_id))
            running.add(task)
            task.add_done_callback(running.discard)
    finally:
        if running:
            await asyncio.gather(*running, return_exceptions=True)
        await close_client()
        await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
