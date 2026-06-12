import asyncio
import base64
import logging
import random
import re
import sys
import time
import traceback
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.config import (
    AI_API_KEY,
    AI_API_URL,
    AI_IMAGE_RESPONSE_FORMAT,
    AI_TIMEOUT,
    AI_MAX_CONCURRENT,
    AI_MIN_REQUEST_INTERVAL_SECONDS,
    AI_RATE_LIMIT_MAX_RETRIES,
    AI_RATE_LIMIT_MIN_RETRY_DELAY_SECONDS,
    AI_RATE_LIMIT_RETRY_DELAY_SECONDS,
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
IMAGE_DOWNLOAD_RETRIES = 2

_semaphore = asyncio.Semaphore(MAX_CONCURRENT)
_rate_limit_lock = asyncio.Lock()
_last_request_at = 0.0

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


@dataclass(frozen=True)
class AIImageResult:
    data_url: str
    model: str
    endpoint: str
    request_quality: str
    request_size: str
    request_response_format: str | None
    response_request_id: str | None
    response_content_type: str | None
    elapsed_seconds: float
    payload_length: int


class AIClient:

    @staticmethod
    async def generate(prompt: str, quality: str, size: str) -> str:
        return (await AIClient.generate_with_metadata(prompt, quality, size)).data_url

    @staticmethod
    async def generate_with_metadata(prompt: str, quality: str, size: str) -> AIImageResult:
        quality_level = QUALITY_LEVEL_MAP.get(quality, "low")
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality_level,
        }
        AIClient._apply_response_format(payload)
        url = f"{AI_API_URL}/images/generations"
        logger.info(f"[AI REQUEST] POST {url} | quality={quality_level} | size={size}")
        return await AIClient._call_api_with_metadata(url, payload, is_json=True)

    @staticmethod
    async def edit(
        image_bytes: bytes,
        prompt: str,
        quality: str,
        size: str,
        filename: str,
        mime_type: str = "image/png",
    ) -> str:
        return (
            await AIClient.edit_with_metadata(
                image_bytes,
                prompt,
                quality,
                size,
                filename,
                mime_type,
            )
        ).data_url

    @staticmethod
    async def edit_with_metadata(
        image_bytes: bytes,
        prompt: str,
        quality: str,
        size: str,
        filename: str,
        mime_type: str = "image/png",
    ) -> AIImageResult:
        quality_level = QUALITY_LEVEL_MAP.get(quality, "low")
        url = f"{AI_API_URL}/images/edits"
        logger.info(f"[AI EDIT REQUEST] POST {url} | quality={quality_level} | size={size} | file={filename}")

        files = {"image": (filename, image_bytes, AIClient._normalize_mime_type(mime_type) or "image/png")}
        form_data = {"model": MODEL_NAME, "prompt": prompt, "n": "1", "size": size, "quality": quality_level}
        AIClient._apply_response_format(form_data)
        return await AIClient._call_api_with_metadata(url, form_data, is_json=False, files=files)

    @staticmethod
    async def _call_api(url, payload, is_json=True, files=None):
        return (await AIClient._call_api_with_metadata(url, payload, is_json, files)).data_url

    @staticmethod
    async def _call_api_with_metadata(url, payload, is_json=True, files=None) -> AIImageResult:
        async with _semaphore:
            wait_start = asyncio.get_event_loop().time()
            if _semaphore.locked():
                logger.info(f"[AI QUEUE] waiting for upstream slot...")

            client = await get_client()
            call_started_at = time.monotonic()
            for attempt in range(1 + AI_RATE_LIMIT_MAX_RETRIES):
                try:
                    await AIClient._wait_for_request_slot()
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

                    data_url = await AIClient._extract_image_data_url(response, client)
                    elapsed_seconds = time.monotonic() - call_started_at

                    if _semaphore._value == 0 and attempt > 0:
                        wait_time = asyncio.get_event_loop().time() - wait_start
                        logger.info(f"[AI RETRY OK] succeeded after {attempt} retries ({wait_time:.1f}s)")

                    logger.info(f"[AI SUCCESS] image generated, data URL length={len(data_url)}")
                    return AIImageResult(
                        data_url=data_url,
                        model=str(payload.get("model") or MODEL_NAME),
                        endpoint=AIClient._endpoint_from_url(url),
                        request_quality=str(payload.get("quality") or ""),
                        request_size=str(payload.get("size") or ""),
                        request_response_format=payload.get("response_format") or None,
                        response_request_id=AIClient._extract_request_id(response),
                        response_content_type=response.headers.get("content-type"),
                        elapsed_seconds=elapsed_seconds,
                        payload_length=len(data_url),
                    )

                except httpx.TimeoutException:
                    logger.error(f"[AI TIMEOUT] request to {url} exceeded {AI_TIMEOUT}s")
                    raise AITimeoutError(f"AI API timeout after {AI_TIMEOUT}s")

                except AIRateLimitError as e:
                    if attempt < AI_RATE_LIMIT_MAX_RETRIES:
                        delay = AIClient._retry_delay(e.retry_after_seconds, attempt)
                        logger.warning(
                            "[AI RATE LIMITED] 429, retry %s/%s after %.2fs: %s",
                            attempt + 1,
                            AI_RATE_LIMIT_MAX_RETRIES,
                            delay,
                            e,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise

                except AIUnsupportedParameterError as e:
                    if AIClient._remove_response_format(payload):
                        logger.warning("[AI COMPAT] retrying without response_format: %s", e)
                        continue
                    raise

                except httpx.ConnectError as e:
                    logger.error(f"[AI CONNECT ERROR] {url}: {e}")
                    raise Exception(f"Cannot connect to AI API: {e}")

                except httpx.HTTPStatusError as e:
                    AIClient._handle_response(e.response, url)
                    raise

                except Exception as e:
                    raise

            raise Exception("AI API failed after all retries")

    @staticmethod
    def _endpoint_from_url(url: str) -> str:
        parsed = urlparse(url)
        return parsed.path or url

    @staticmethod
    def _extract_request_id(response: httpx.Response) -> str | None:
        for header in (
            "x-request-id",
            "x-openai-request-id",
            "openai-request-id",
            "request-id",
        ):
            value = response.headers.get(header)
            if value:
                return value
        return None

    @staticmethod
    def _apply_response_format(payload: dict) -> None:
        if AI_IMAGE_RESPONSE_FORMAT in {"url", "b64_json"}:
            payload["response_format"] = AI_IMAGE_RESPONSE_FORMAT

    @staticmethod
    def _remove_response_format(payload: dict) -> bool:
        return payload.pop("response_format", None) is not None

    @staticmethod
    async def _wait_for_request_slot() -> None:
        global _last_request_at
        if AI_MIN_REQUEST_INTERVAL_SECONDS <= 0:
            return
        async with _rate_limit_lock:
            now = asyncio.get_event_loop().time()
            wait_seconds = _last_request_at + AI_MIN_REQUEST_INTERVAL_SECONDS - now
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            _last_request_at = asyncio.get_event_loop().time()

    @staticmethod
    def _retry_delay(retry_after_seconds: float | None, attempt: int) -> float:
        base_delay = retry_after_seconds
        if base_delay is None:
            base_delay = AI_RATE_LIMIT_RETRY_DELAY_SECONDS * (2 ** attempt)
        base_delay = max(base_delay, AI_RATE_LIMIT_MIN_RETRY_DELAY_SECONDS)
        jitter = random.uniform(0, min(0.25, base_delay * 0.2))
        return min(max(base_delay + jitter, 0.1), 30.0)

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
            if response.status_code == 429:
                retry_after = AIClient._parse_retry_after(response, detail)
                logger.warning(f"[AI RATE LIMIT] {detail}")
                raise AIRateLimitError(detail, retry_after)
            if response.status_code == 400 and AIClient._is_unsupported_response_format_error(detail):
                raise AIUnsupportedParameterError(detail)
            logger.error(f"[AI ERROR] {response.status_code}: {detail}")
            raise Exception(f"AI API error ({response.status_code}): {detail}")

    @staticmethod
    def _is_unsupported_response_format_error(detail: str) -> bool:
        normalized = detail.lower()
        if "response_format" not in normalized:
            return False
        return any(
            marker in normalized
            for marker in (
                "unknown",
                "unsupported",
                "invalid",
                "not support",
                "not supported",
                "does not support",
                "unrecognized",
                "unexpected",
            )
        )

    @staticmethod
    def _parse_retry_after(response: httpx.Response, detail: str) -> float | None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                pass

        match = re.search(r"try again in\s+(\d+(?:\.\d+)?)\s*ms", detail, re.IGNORECASE)
        if match:
            return max(float(match.group(1)) / 1000, 0.0)

        match = re.search(r"try again in\s+(\d+(?:\.\d+)?)\s*s", detail, re.IGNORECASE)
        if match:
            return max(float(match.group(1)), 0.0)

        return None

    @staticmethod
    async def _extract_image_data_url(response: httpx.Response, client: httpx.AsyncClient) -> str:
        content_type = AIClient._normalize_mime_type(response.headers.get("content-type"))
        if content_type or AIClient._guess_mime_type(response.content):
            return AIClient._bytes_to_data_url(response.content, content_type)

        try:
            data = response.json()
        except ValueError as exc:
            raise AIResponsePayloadError("AI API returned a successful non-JSON response without image bytes") from exc

        try:
            item = data["data"][0]
        except (TypeError, KeyError, IndexError) as exc:
            raise AIResponsePayloadError(f"AI API returned no image data ({AIClient._describe_payload(data)})") from exc

        if not isinstance(item, dict):
            raise AIResponsePayloadError("AI API image item is not an object")

        b64_json = item.get("b64_json")
        if isinstance(b64_json, str) and b64_json.strip():
            mime_type = AIClient._normalize_mime_type(
                item.get("mime_type") or item.get("content_type") or "image/png"
            )
            return f"data:{mime_type or 'image/png'};base64,{b64_json}"

        image_url = AIClient._extract_image_url(item)
        if image_url:
            if image_url.startswith("data:image/"):
                return image_url
            try:
                return await AIClient._download_image_as_data_url(client, image_url)
            except RemoteImageDownloadError as exc:
                logger.warning("[AI URL FALLBACK] using remote image URL because backend download failed: %s", exc)
                return image_url

        keys = ", ".join(sorted(str(key) for key in item.keys()))
        raise AIResponsePayloadError(f"AI API image item missing b64_json/url fields (keys: {keys})")

    @staticmethod
    def _extract_image_url(item: dict) -> str | None:
        for key in ("url", "image_url", "output_url"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                nested_url = value.get("url")
                if isinstance(nested_url, str) and nested_url.strip():
                    return nested_url.strip()
        return None

    @staticmethod
    async def _download_image_as_data_url(client: httpx.AsyncClient, image_url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(IMAGE_DOWNLOAD_RETRIES + 1):
            try:
                response = await client.get(image_url, follow_redirects=True)
                if response.status_code != 200:
                    raise RemoteImageDownloadError(
                        image_url,
                        f"image URL returned HTTP {response.status_code}",
                    )

                mime_type = AIClient._mime_type_from_response(response, image_url)
                return AIClient._bytes_to_data_url(response.content, mime_type)
            except (httpx.HTTPError, RemoteImageDownloadError) as exc:
                last_error = exc
                if attempt < IMAGE_DOWNLOAD_RETRIES:
                    await asyncio.sleep(attempt + 1)

        raise RemoteImageDownloadError(
            image_url,
            f"AI API returned an image URL, but backend could not download it: {last_error}",
        )

    @staticmethod
    def _bytes_to_data_url(image_bytes: bytes, mime_type: str | None) -> str:
        if not image_bytes:
            raise AIResponsePayloadError("AI API returned empty image bytes")
        normalized_mime = AIClient._normalize_mime_type(mime_type) or AIClient._guess_mime_type(image_bytes)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{normalized_mime};base64,{encoded}"

    @staticmethod
    def _mime_type_from_response(response: httpx.Response, image_url: str) -> str:
        raw_content_type = response.headers.get("content-type")
        content_type = AIClient._normalize_mime_type(raw_content_type)
        if content_type:
            return content_type
        guessed_mime = AIClient._guess_mime_type(response.content)
        if guessed_mime:
            return guessed_mime

        raw_mime = str(raw_content_type or "").split(";")[0].strip().lower()
        if raw_mime in {"", "application/octet-stream", "binary/octet-stream"}:
            extension_mime = AIClient._mime_type_from_url(image_url)
            if extension_mime:
                return extension_mime

        raise AIResponsePayloadError(f"image URL did not return image bytes (content-type: {raw_mime or 'unknown'})")

    @staticmethod
    def _normalize_mime_type(mime_type: str | None) -> str | None:
        if not mime_type:
            return None
        normalized = str(mime_type).split(";")[0].strip().lower()
        if normalized == "image/jpg":
            return "image/jpeg"
        if normalized in {"image/png", "image/jpeg", "image/webp"}:
            return normalized
        return None

    @staticmethod
    def _mime_type_from_url(image_url: str) -> str | None:
        path = image_url.split("?", 1)[0].split("#", 1)[0].lower()
        if path.endswith(".png"):
            return "image/png"
        if path.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        if path.endswith(".webp"):
            return "image/webp"
        return None

    @staticmethod
    def _guess_mime_type(image_bytes: bytes) -> str | None:
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        return None

    @staticmethod
    def _describe_payload(data) -> str:
        if isinstance(data, dict):
            return f"top-level keys: {', '.join(sorted(str(key) for key in data.keys()))}"
        return f"payload type: {type(data).__name__}"


class AIResponsePayloadError(Exception):
    pass


class RemoteImageDownloadError(AIResponsePayloadError):
    def __init__(self, image_url: str, message: str) -> None:
        super().__init__(message)
        self.image_url = image_url


class AITimeoutError(Exception):
    pass


class AIRateLimitError(Exception):
    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class AIUnsupportedParameterError(Exception):
    pass
