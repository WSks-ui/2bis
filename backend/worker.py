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
from app.logging_config import configure_logging
from app.models import GenerateHistory, GenerationTask, GenerationTaskStatus
from app.services.ai_client import (
    AIAuthenticationError,
    AIClient,
    AIImageResult,
    AIInsufficientCreditsError,
    AIResponseBodyTimeoutError,
    AIResponsePayloadError,
    AIResponseInterruptedError,
    AIUpstreamServerError,
    AIUnsupportedParameterError,
    AITimeoutError,
    close_client,
    get_client,
)
from app.services.generation_options import GenerationOptions
from app.services.image_storage import save_data_url
from app.services.quota_manager import QuotaManager
from app.services.task_queue import close_redis, dequeue_generation_task, enqueue_generation_task
from app.services.upload_storage import read_upload_file

logger = logging.getLogger("generation_worker")
configure_logging()

_remote_mirror_tasks: set[asyncio.Task] = set()
_remote_mirror_semaphore = asyncio.Semaphore(2)


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


async def update_task_progress(
    task_id: int,
    stage: str,
    message: str | None,
    response=None,
) -> None:
    async with async_session() as db:
        task = await db.get(GenerationTask, task_id)
        if task is None:
            return
        task.progress_stage = stage
        task.progress_message = message
        if response is not None:
            task.upstream_request_id = AIClient._extract_request_id(response)
            task.upstream_content_type = response.headers.get("content-type")
        await db.commit()


def format_bytes(value: int | None) -> str:
    if value is None:
        return "未知大小"
    units = ("B", "KB", "MB", "GB")
    size = float(max(value, 0))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)}{unit}"
            return f"{size:.1f}{unit}"
        size /= 1024


def receiving_progress_message(received_bytes: int, total_bytes: int | None, elapsed_seconds: float) -> str:
    speed = received_bytes / elapsed_seconds if elapsed_seconds > 0 else 0.0
    if total_bytes:
        return (
            f"正在接收图片数据：{format_bytes(received_bytes)} / "
            f"{format_bytes(total_bytes)}，平均 {format_bytes(int(speed))}/s"
        )
    return f"正在接收图片数据：{format_bytes(received_bytes)}，平均 {format_bytes(int(speed))}/s"


def schedule_remote_image_mirror(task_id: int, user_id: int, remote_url: str | None) -> None:
    if not remote_url or not remote_url.startswith(("http://", "https://")):
        return

    task = asyncio.create_task(mirror_remote_image(task_id, user_id, remote_url))
    _remote_mirror_tasks.add(task)
    task.add_done_callback(_remote_mirror_tasks.discard)


async def mirror_remote_image(task_id: int, user_id: int, remote_url: str) -> None:
    started_at = time.monotonic()
    try:
        async with _remote_mirror_semaphore:
            client = await get_client()
            data_url = await AIClient._download_image_as_data_url(client, remote_url)
            local_url = await save_data_url(data_url, user_id)
        if not local_url or local_url == remote_url:
            return

        async with async_session() as db:
            task = await db.get(GenerationTask, task_id)
            if task is not None and task.image_url == remote_url:
                task.image_url = local_url

            result = await db.execute(
                select(GenerateHistory).where(
                    GenerateHistory.task_id == task_id,
                    GenerateHistory.user_id == user_id,
                )
            )
            history = result.scalar_one_or_none()
            if history is not None and history.image_url == remote_url:
                history.image_url = local_url

            await db.commit()

        logger.info(
            "task %s remote image mirrored in %.1fs: %s",
            task_id,
            time.monotonic() - started_at,
            local_url,
        )
    except Exception as exc:
        logger.warning("task %s remote image mirror skipped: %s", task_id, exc)


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
            task.progress_stage = "failed"
            task.progress_message = "任务处理进程中断，额度已退回。"
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
        task.progress_stage = "requesting"
        task.progress_message = "正在请求上游生成服务。"
        task.error_message = None
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
        async def mark_response_headers_received(response) -> None:
            await update_task_progress(
                task_id,
                "receiving",
                "上游已返回生成结果，正在接收图片数据。",
                response,
            )

        last_progress_update_at = 0.0
        last_progress_update_bytes = 0

        async def mark_body_progress(
            received_bytes: int,
            total_bytes: int | None,
            elapsed_seconds: float,
        ) -> None:
            nonlocal last_progress_update_at, last_progress_update_bytes
            now = time.monotonic()
            should_update = (
                now - last_progress_update_at >= 30
                or received_bytes - last_progress_update_bytes >= 5 * 1024 * 1024
                or (total_bytes is not None and received_bytes >= total_bytes)
            )
            if not should_update:
                return
            last_progress_update_at = now
            last_progress_update_bytes = received_bytes
            await update_task_progress(
                task_id,
                "receiving",
                receiving_progress_message(received_bytes, total_bytes, elapsed_seconds),
            )

        if task.mode == "text2img":
            ai_result = await asyncio.wait_for(
                AIClient.generate_with_metadata(
                    task.prompt,
                    task.quality,
                    task.size,
                    on_response_headers=mark_response_headers_received,
                    on_body_progress=mark_body_progress,
                ),
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
                    on_response_headers=mark_response_headers_received,
                    on_body_progress=mark_body_progress,
                ),
                timeout=GENERATION_TASK_TIMEOUT,
            )
        raw_data_url = ai_result.data_url
        upstream_seconds = time.monotonic() - upstream_started_at
        logger.info(
            (
                "task %s upstream response complete total=%.1fs header=%.1fs body=%.1fs parse=%.3fs "
                "request_quality=%s request_id=%s source=%s payload_length=%s"
            ),
            task_id,
            upstream_seconds,
            ai_result.header_seconds or 0.0,
            ai_result.body_seconds or 0.0,
            ai_result.parse_seconds or 0.0,
            ai_result.request_quality,
            ai_result.response_request_id,
            "url" if ai_result.image_url else "data",
            len(ai_result.image_url or raw_data_url or ""),
        )

        save_started_at = time.monotonic()
        await update_task_progress(task_id, "saving", "图片已接收，正在保存到本地。")
        image_url = ai_result.image_url or await save_data_url(raw_data_url, task.user_id)
        save_seconds = time.monotonic() - save_started_at
        logger.info("task %s image result stored in %.1fs: %s", task_id, save_seconds, image_url)

        async with async_session() as db:
            result = await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

            task.status = GenerationTaskStatus.SUCCESS
            task.image_url = image_url
            task.error_message = None
            task.progress_stage = "completed"
            task.progress_message = None
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

        schedule_remote_image_mirror(task_id, task.user_id, ai_result.image_url)
    except Exception as e:
        async with async_session() as db:
            result = await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

            task.retry_count += 1
            task.error_message = str(e)
            task.progress_stage = "retrying"
            task.progress_message = "生成失败，正在准备重试。"
            task.locked_at = None

            can_retry = not isinstance(
                e,
                (
                    AIResponsePayloadError,
                    AIResponseInterruptedError,
                    AIResponseBodyTimeoutError,
                    AIAuthenticationError,
                    AIInsufficientCreditsError,
                    AIUnsupportedParameterError,
                    AIUpstreamServerError,
                    AITimeoutError,
                ),
            ) and task.retry_count <= task.max_retries
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
            task.progress_stage = "failed"
            task.progress_message = "生成未能完成，已自动退回额度。"
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
