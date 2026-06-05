import asyncio
import logging
import sys
import traceback

import httpx

from app.config import (
    AI_API_KEY,
    AI_API_URL,
    AI_TIMEOUT,
    AI_MAX_CONCURRENT,
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEPALIVE,
)

logger = logging.getLogger("ai_client")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
    logger.addHandler(handler)

MODEL_NAME = "gpt-image-2"
MAX_CONCURRENT = AI_MAX_CONCURRENT
MAX_RETRIES = 2

_semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# 模块级 httpx client 单例, 复用连接池, 避免每次请求新建 TCP 连接导致 socket 耗尽
_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = httpx.AsyncClient(
                    timeout=AI_TIMEOUT,
                    proxy=None,
                    trust_env=False,
                    limits=httpx.Limits(
                        max_connections=HTTP_MAX_CONNECTIONS,
                        max_keepalive_connections=HTTP_MAX_KEEPALIVE,
                    ),
                )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

QUALITY_LEVEL_MAP = {
    "low": "low",
    "medium": "medium",
    "high": "high",
}


class AIClient:

    @staticmethod
    async def generate(prompt: str, quality: str, size: str) -> str:
        quality_level = QUALITY_LEVEL_MAP.get(quality, "low")
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality_level,
        }
        url = f"{AI_API_URL}/images/generations"
        logger.info(f"[AI REQUEST] POST {url} | quality={quality_level} | size={size}")
        return await AIClient._call_api(url, payload, is_json=True)

    @staticmethod
    async def edit(image_bytes: bytes, prompt: str, quality: str, size: str, filename: str) -> str:
        quality_level = QUALITY_LEVEL_MAP.get(quality, "low")
        url = f"{AI_API_URL}/images/edits"
        logger.info(f"[AI EDIT REQUEST] POST {url} | quality={quality_level} | size={size} | file={filename}")

        files = {"image": (filename, image_bytes, "image/png")}
        form_data = {"model": MODEL_NAME, "prompt": prompt, "n": "1", "size": size, "quality": quality_level}
        return await AIClient._call_api(url, form_data, is_json=False, files=files)

    @staticmethod
    async def _call_api(url, payload, is_json=True, files=None):
        async with _semaphore:
            wait_start = asyncio.get_event_loop().time()
            if _semaphore.locked():
                logger.info(f"[AI QUEUE] waiting for upstream slot...")

            client = await get_client()
            for attempt in range(1 + MAX_RETRIES):
                try:
                    if is_json:
                        response = await client.post(
                            url,
                            json=payload,
                            headers={"Authorization": f"Bearer {AI_API_KEY}"},
                        )
                    else:
                        response = await client.post(
                            url,
                            files=files,
                            data=payload,
                            headers={"Authorization": f"Bearer {AI_API_KEY}"},
                        )

                    AIClient._handle_response(response, url)

                    data = response.json()
                    b64_json = data["data"][0]["b64_json"]

                    if _semaphore._value == 0 and attempt > 0:
                        wait_time = asyncio.get_event_loop().time() - wait_start
                        logger.info(f"[AI RETRY OK] succeeded after {attempt} retries ({wait_time:.1f}s)")

                    logger.info(f"[AI SUCCESS] image generated, base64 length={len(b64_json)}")
                    return f"data:image/png;base64,{b64_json}"

                except httpx.TimeoutException:
                    logger.error(f"[AI TIMEOUT] request to {url} exceeded {AI_TIMEOUT}s")
                    raise Exception(f"AI API timeout after {AI_TIMEOUT}s")

                except httpx.ConnectError as e:
                    logger.error(f"[AI CONNECT ERROR] {url}: {e}")
                    raise Exception(f"Cannot connect to AI API: {e}")

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < MAX_RETRIES:
                        delay = (attempt + 1) * 3
                        logger.warning(f"[AI RATE LIMITED] 429, retry {attempt + 1}/{MAX_RETRIES} after {delay}s")
                        await asyncio.sleep(delay)
                        continue
                    AIClient._handle_response(e.response, url)
                    raise

                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg and attempt < MAX_RETRIES:
                        delay = (attempt + 1) * 3
                        logger.warning(f"[AI RATE LIMITED] retry {attempt + 1}/{MAX_RETRIES} after {delay}s")
                        await asyncio.sleep(delay)
                        continue
                    raise

            raise Exception("AI API failed after all retries")

    @staticmethod
    def _handle_response(response, url):
        logger.info(f"[AI RESPONSE] status={response.status_code}")
        if response.status_code != 200:
            detail = response.text
            try:
                err = response.json()
                detail = err.get("error", {}).get("message", detail)
            except Exception:
                pass
            logger.error(f"[AI ERROR] {response.status_code}: {detail}")
            raise Exception(f"AI API error ({response.status_code}): {detail}")
