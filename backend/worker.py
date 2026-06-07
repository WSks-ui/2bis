import asyncio
import logging
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
from app.services.ai_client import AIClient, close_client
from app.services.image_storage import save_data_url
from app.services.point_manager import PointManager
from app.services.task_queue import close_redis, dequeue_generation_task, enqueue_generation_task
from app.services.upload_storage import read_upload_file

logger = logging.getLogger("generation_worker")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")


async def recover_stale_processing_tasks() -> None:
    cutoff = datetime.utcnow() - timedelta(seconds=GENERATION_PROCESSING_RECOVERY_SECONDS)
    async with async_session() as db:
        result = await db.execute(
            select(GenerationTask).where(
                GenerationTask.status == GenerationTaskStatus.PROCESSING,
                or_(GenerationTask.locked_at.is_(None), GenerationTask.locked_at < cutoff),
                GenerationTask.retry_count < GenerationTask.max_retries,
            )
        )
        tasks = result.scalars().all()
        for task in tasks:
            task.status = GenerationTaskStatus.PENDING
            task.locked_at = None
            await enqueue_generation_task(task.id)
        await db.commit()
        if tasks:
            logger.warning("recovered %s stale processing tasks", len(tasks))


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
        async with async_session() as db:
            result = await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

        if task.mode == "text2img":
            raw_data_url = await asyncio.wait_for(
                AIClient.generate(task.prompt, task.quality, task.size),
                timeout=GENERATION_TASK_TIMEOUT,
            )
        else:
            image_bytes = await read_upload_file(task.source_image_path)
            raw_data_url = await asyncio.wait_for(
                AIClient.edit(image_bytes, task.prompt, task.quality, task.size, "image.png"),
                timeout=GENERATION_TASK_TIMEOUT,
            )

        image_url = await save_data_url(raw_data_url, task.user_id)

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
            history_prompt = f"[图生图] {task.prompt}" if task.mode != "text2img" else task.prompt
            history = GenerateHistory(
                user_id=task.user_id,
                task_id=task.id,
                prompt=history_prompt,
                image_url=image_url,
                quality=task.quality,
                points_cost=task.points_cost,
                created_at=task.finished_at,
            )
            db.add(history)
            await db.commit()
            logger.info("task %s success", task_id)
    except Exception as e:
        async with async_session() as db:
            result = await db.execute(select(GenerationTask).where(GenerationTask.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

            task.retry_count += 1
            task.error_message = str(e)
            task.locked_at = None

            if task.retry_count <= task.max_retries:
                task.status = GenerationTaskStatus.PENDING
                await db.commit()
                await enqueue_generation_task(task.id)
                logger.exception("task %s failed, retry %s/%s", task_id, task.retry_count, task.max_retries)
                return

            await PointManager.add_points(db, task.user_id, task.points_cost)
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
