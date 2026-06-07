import logging

import redis.asyncio as redis

from app.config import GENERATION_QUEUE_NAME, REDIS_URL

logger = logging.getLogger("task_queue")

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is not None:
        return _redis

    _redis = redis.from_url(REDIS_URL, decode_responses=True)
    await _redis.ping()
    logger.info("connected to Redis at %s", REDIS_URL)
    return _redis


async def enqueue_generation_task(task_id: int) -> None:
    client = await get_redis()
    await client.lpush(GENERATION_QUEUE_NAME, str(task_id))


async def dequeue_generation_task(timeout: int = 5) -> int | None:
    client = await get_redis()
    item = await client.brpop(GENERATION_QUEUE_NAME, timeout=timeout)
    if item is None:
        return None
    return int(item[1])


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
