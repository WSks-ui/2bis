import asyncio
import base64
import logging
import random
import re
import time
import traceback
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.config import (
    AI_API_KEY,
    AI_API_URL,
    AI_IMAGE_RESPONSE_FORMAT,
    AI_RESPONSE_FORMAT_FALLBACK,
    AI_RESPONSE_BODY_TIMEOUT,
    AI_TIMEOUT,
    AI_MAX_CONCURRENT,
    AI_MIN_REQUEST_INTERVAL_SECONDS,
    AI_RATE_LIMIT_MAX_RETRIES,
    AI_RATE_LIMIT_MIN_RETRY_DELAY_SECONDS,
    AI_RATE_LIMIT_RETRY_DELAY_SECONDS,
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEPALIVE,
)
from app.services.api_key_manager import (
    ActiveApiConfig,
    get_active_api_config,
    invalidate_active_api_config_cache,
    mark_api_config_failed,
    touch_api_config_used,
)

logger = logging.getLogger("ai_client")

MODEL_NAME = "gpt-image-2"
MAX_CONCURRENT = AI_MAX_CONCURRENT
MAX_RETRIES = 2
IMAGE_DOWNLOAD_RETRIES = 2
RESPONSE_FORMAT_UNSUPPORTED_HOSTS = {"aiartmirror.com", "www.aiartmirror.com"}
MAX_API_CONFIG_SWITCHES = 2
RESPONSE_BODY_PROGRESS_INTERVAL_SECONDS = 30.0
RESPONSE_BODY_PROGRESS_BYTES = 5 * 1024 * 1024

BodyProgressCallback = Callable[[int, int | None, float], Awaitable[None]]

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
    image_url: str | None
    model: str
    endpoint: str
    request_quality: str
    request_size: str
    request_response_format: str | None
    response_request_id: str | None
    response_content_type: str | None
    elapsed_seconds: float
    payload_length: int
    header_seconds: float | None = None
    body_seconds: float | None = None
    parse_seconds: float | None = None

    @property
    def display_url(self) -> str:
        return self.image_url or self.data_url


class AIClient:

    @staticmethod
    async def generate(prompt: str, quality: str, size: str) -> str:
        return (await AIClient.generate_with_metadata(prompt, quality, size)).display_url

    @staticmethod
    async def generate_with_metadata(
        prompt: str,
        quality: str,
        size: str,
        on_response_headers: Callable[[httpx.Response], Awaitable[None]] | None = None,
        on_body_progress: BodyProgressCallback | None = None,
    ) -> AIImageResult:
        return await AIClient.generate_with_metadata_for_task(
            prompt,
            quality,
            size,
            on_response_headers=on_response_headers,
            on_body_progress=on_body_progress,
        )

    @staticmethod
    async def generate_with_metadata_for_task(
        prompt: str,
        quality: str,
        size: str,
        on_response_headers: Callable[[httpx.Response], Awaitable[None]] | None = None,
        on_body_progress: BodyProgressCallback | None = None,
    ) -> AIImageResult:
        quality_level = QUALITY_LEVEL_MAP.get(quality, "low")
        base_payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality_level,
        }
        return await AIClient._call_api_with_key_failover(
            endpoint="/images/generations",
            payload=base_payload,
            is_json=True,
            log_label=f"[AI REQUEST] quality={quality_level} | size={size}",
            on_response_headers=on_response_headers,
            on_body_progress=on_body_progress,
        )

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
        ).display_url

    @staticmethod
    async def edit_with_metadata(
        image_bytes: bytes,
        prompt: str,
        quality: str,
        size: str,
        filename: str,
        mime_type: str = "image/png",
        on_response_headers: Callable[[httpx.Response], Awaitable[None]] | None = None,
        on_body_progress: BodyProgressCallback | None = None,
    ) -> AIImageResult:
        return await AIClient.edit_with_metadata_for_task(
            image_bytes,
            prompt,
            quality,
            size,
            filename,
            mime_type,
            on_response_headers=on_response_headers,
            on_body_progress=on_body_progress,
        )

    @staticmethod
    async def edit_with_metadata_for_task(
        image_bytes: bytes,
        prompt: str,
        quality: str,
        size: str,
        filename: str,
        mime_type: str = "image/png",
        on_response_headers: Callable[[httpx.Response], Awaitable[None]] | None = None,
        on_body_progress: BodyProgressCallback | None = None,
    ) -> AIImageResult:
        quality_level = QUALITY_LEVEL_MAP.get(quality, "low")
        files = {"image": (filename, image_bytes, AIClient._normalize_mime_type(mime_type) or "image/png")}
        form_data = {"model": MODEL_NAME, "prompt": prompt, "n": "1", "size": size, "quality": quality_level}
        return await AIClient._call_api_with_key_failover(
            endpoint="/images/edits",
            payload=form_data,
            is_json=False,
            files=files,
            log_label=f"[AI EDIT REQUEST] quality={quality_level} | size={size} | file={filename}",
            on_response_headers=on_response_headers,
            on_body_progress=on_body_progress,
        )

    @staticmethod
    async def _call_api(url, payload, is_json=True, files=None):
        return (await AIClient._call_api_with_metadata(url, payload, is_json, files)).display_url

    @staticmethod
    async def _call_api_with_key_failover(
        endpoint: str,
        payload: dict,
        is_json: bool = True,
        files=None,
        log_label: str = "[AI REQUEST]",
        on_response_headers: Callable[[httpx.Response], Awaitable[None]] | None = None,
        on_body_progress: BodyProgressCallback | None = None,
    ) -> AIImageResult:
        attempted_config_ids: set[int | None] = set()
        last_error: Exception | None = None
        for switch_index in range(MAX_API_CONFIG_SWITCHES + 1):
            api_config = await get_active_api_config(force_refresh=switch_index > 0)
            if api_config.config_id in attempted_config_ids:
                break
            attempted_config_ids.add(api_config.config_id)

            request_payload = dict(payload)
            AIClient._apply_provider_payload_options(request_payload, api_config)
            AIClient._apply_response_format(request_payload, api_config)
            url = f"{api_config.api_url}{endpoint}"
            logger.info(
                "%s | POST %s | key=%s | payload=%s",
                log_label,
                url,
                api_config.key_mask or "env",
                AIClient._summarize_request_payload(request_payload),
            )

            try:
                return await AIClient._call_api_with_metadata(
                    url,
                    request_payload,
                    is_json=is_json,
                    files=files,
                    api_config=api_config,
                    on_response_headers=on_response_headers,
                    on_body_progress=on_body_progress,
                )
            except AIKeyTerminalError as exc:
                last_error = exc
                await mark_api_config_failed(
                    api_config.config_id,
                    str(exc),
                    terminal=True,
                )
                invalidate_active_api_config_cache()
                logger.warning(
                    "[AI KEY FAILOVER] key=%s opened circuit after terminal error: %s",
                    api_config.key_mask or "env",
                    exc,
                )
                continue

        if last_error is not None:
            raise last_error
        raise Exception("No available AI API key configuration")

    @staticmethod
    async def _call_api_with_metadata(
        url,
        payload,
        is_json=True,
        files=None,
        api_config: ActiveApiConfig | None = None,
        on_response_headers: Callable[[httpx.Response], Awaitable[None]] | None = None,
        on_body_progress: BodyProgressCallback | None = None,
    ) -> AIImageResult:
        auth_token = api_config.api_key if api_config is not None else AI_API_KEY
        async with _semaphore:
            wait_start = asyncio.get_event_loop().time()
            if _semaphore.locked():
                logger.info(f"[AI QUEUE] waiting for upstream slot...")

            client = await get_client()
            call_started_at = time.monotonic()
            for attempt in range(1 + AI_RATE_LIMIT_MAX_RETRIES):
                try:
                    await AIClient._wait_for_request_slot()
                    response, header_seconds, body_seconds = await AIClient._post_and_read_response(
                        client=client,
                        url=url,
                        payload=payload,
                        is_json=is_json,
                        files=files,
                        auth_token=auth_token,
                        on_response_headers=on_response_headers,
                        on_body_progress=on_body_progress,
                    )
                    AIClient._handle_response(response, url)
                    parse_started_at = time.monotonic()
                    data_url, image_url = await AIClient._extract_image_result_with_timeout(response, client)
                    parse_seconds = time.monotonic() - parse_started_at
                    elapsed_seconds = time.monotonic() - call_started_at

                    if _semaphore._value == 0 and attempt > 0:
                        wait_time = asyncio.get_event_loop().time() - wait_start
                        logger.info(f"[AI RETRY OK] succeeded after {attempt} retries ({wait_time:.1f}s)")

                    logger.info(
                        "[AI SUCCESS] image generated, source=%s, payload length=%s, total=%.1fs, header=%.1fs, body=%.1fs, parse=%.3fs",
                        "url" if image_url else "data",
                        len(image_url or data_url),
                        elapsed_seconds,
                        header_seconds,
                        body_seconds,
                        parse_seconds,
                    )
                    await touch_api_config_used(api_config.config_id if api_config else None)
                    return AIImageResult(
                        data_url=data_url,
                        image_url=image_url,
                        model=str(payload.get("model") or MODEL_NAME),
                        endpoint=AIClient._endpoint_from_url(url),
                        request_quality=str(payload.get("quality") or ""),
                        request_size=str(payload.get("size") or ""),
                        request_response_format=payload.get("response_format") or None,
                        response_request_id=AIClient._extract_request_id(response),
                        response_content_type=response.headers.get("content-type"),
                        elapsed_seconds=elapsed_seconds,
                        header_seconds=header_seconds,
                        body_seconds=body_seconds,
                        parse_seconds=parse_seconds,
                        payload_length=len(image_url or data_url),
                    )

                except httpx.TimeoutException:
                    logger.error(f"[AI TIMEOUT] request to {url} exceeded {AI_TIMEOUT}s")
                    await mark_api_config_failed(
                        api_config.config_id if api_config else None,
                        f"AI API timeout after {AI_TIMEOUT}s",
                    )
                    raise AITimeoutError(f"AI API timeout after {AI_TIMEOUT}s")

                except httpx.RemoteProtocolError as e:
                    message = str(e)
                    logger.error("[AI RESPONSE INTERRUPTED] %s: %s", url, message)
                    raise AIResponseInterruptedError(
                        "上游图片响应传输中断。系统已停止自动重试以避免重复生成和重复扣费；"
                        "当前上游不支持 response_format=url，请更换支持 URL 返回的接口，"
                        "或继续使用当前 base64 响应并降低单次图片传输体积。"
                    ) from e

                except AIResponseBodyTimeoutError:
                    logger.error(
                        "[AI RESPONSE BODY TIMEOUT] %s body was not fully received within %ss",
                        url,
                        AI_RESPONSE_BODY_TIMEOUT,
                    )
                    raise

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
                    await mark_api_config_failed(
                        api_config.config_id if api_config else None,
                        str(e),
                    )
                    raise

                except AIUnsupportedParameterError as e:
                    if AI_RESPONSE_FORMAT_FALLBACK and AIClient._remove_response_format(payload):
                        logger.warning("[AI COMPAT] retrying without response_format: %s", e)
                        continue
                    raise

                except AIUpstreamServerError as e:
                    logger.error("[AI UPSTREAM SERVER ERROR] %s: %s", url, e)
                    await mark_api_config_failed(
                        api_config.config_id if api_config else None,
                        str(e),
                    )
                    raise

                except httpx.ConnectError as e:
                    logger.error(f"[AI CONNECT ERROR] {url}: {e}")
                    await mark_api_config_failed(
                        api_config.config_id if api_config else None,
                        f"Cannot connect to AI API: {e}",
                    )
                    raise Exception(f"Cannot connect to AI API: {e}")

                except httpx.HTTPStatusError as e:
                    AIClient._handle_response(e.response, url)
                    raise

                except Exception as e:
                    raise

            raise Exception("AI API failed after all retries")

    @staticmethod
    async def _post_and_read_response(
        client: httpx.AsyncClient,
        url: str,
        payload: dict,
        is_json: bool,
        files,
        auth_token: str,
        on_response_headers: Callable[[httpx.Response], Awaitable[None]] | None = None,
        on_body_progress: BodyProgressCallback | None = None,
    ) -> tuple[httpx.Response, float, float]:
        request_kwargs = (
            {"json": payload}
            if is_json
            else {"files": files, "data": payload}
        )
        request_started_at = time.monotonic()
        async with client.stream(
            "POST",
            url,
            headers={"Authorization": f"Bearer {auth_token}"},
            **request_kwargs,
        ) as response:
            header_seconds = time.monotonic() - request_started_at
            logger.info(
                "[AI HEADERS] status=%s after %.1fs | content-type=%s | content-length=%s | request-id=%s",
                response.status_code,
                header_seconds,
                response.headers.get("content-type") or "-",
                response.headers.get("content-length") or "-",
                AIClient._extract_request_id(response) or "-",
            )
            if response.status_code == 200 and on_response_headers is not None:
                await on_response_headers(response)
            body_progress_callback = on_body_progress if response.status_code == 200 else None
            body_seconds, body_bytes = await AIClient._read_response_body_with_timeout(
                response,
                url,
                on_body_progress=body_progress_callback,
            )
            logger.info(
                "[AI BODY] received %s bytes in %.1fs | total since POST %.1fs",
                body_bytes,
                body_seconds,
                time.monotonic() - request_started_at,
            )
            return response, header_seconds, body_seconds

    @staticmethod
    async def _read_response_body_with_timeout(
        response: httpx.Response,
        url: str,
        on_body_progress: BodyProgressCallback | None = None,
    ) -> tuple[float, int]:
        read_started_at = time.monotonic()
        chunks: list[bytes] = []
        received_bytes = 0
        last_log_at = read_started_at
        last_callback_at = read_started_at
        last_log_bytes = 0
        last_callback_bytes = 0
        content_length = AIClient._parse_content_length(response.headers.get("content-length"))
        activity_event = asyncio.Event()
        read_complete = asyncio.Event()
        read_error: BaseException | None = None

        async def read_stream() -> None:
            nonlocal received_bytes, read_error
            try:
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    received_bytes += len(chunk)
                    activity_event.set()
            except BaseException as exc:
                read_error = exc
            finally:
                activity_event.set()
                read_complete.set()

        reader_task = asyncio.create_task(read_stream())

        try:
            while True:
                now = time.monotonic()
                elapsed = now - read_started_at
                remaining_timeout = AI_RESPONSE_BODY_TIMEOUT - elapsed
                if remaining_timeout <= 0:
                    raise asyncio.TimeoutError
                if read_complete.is_set():
                    if read_error is not None:
                        raise read_error
                    break

                wait_timeout = min(RESPONSE_BODY_PROGRESS_INTERVAL_SECONDS, remaining_timeout)
                activity_event.clear()
                if read_complete.is_set():
                    if read_error is not None:
                        raise read_error
                    break
                try:
                    await asyncio.wait_for(asyncio.shield(activity_event.wait()), timeout=wait_timeout)
                except asyncio.TimeoutError:
                    now = time.monotonic()
                    elapsed = now - read_started_at
                    if elapsed >= AI_RESPONSE_BODY_TIMEOUT:
                        raise
                    AIClient._log_body_progress(
                        url,
                        received_bytes,
                        content_length,
                        elapsed,
                        waiting=True,
                    )
                    if on_body_progress is not None and now - last_callback_at >= RESPONSE_BODY_PROGRESS_INTERVAL_SECONDS:
                        with suppress(Exception):
                            await on_body_progress(received_bytes, content_length, elapsed)
                        last_callback_at = now
                        last_callback_bytes = received_bytes
                    continue

                if read_error is not None:
                    raise read_error

                new_bytes = received_bytes - last_log_bytes
                if new_bytes > 0:
                    now = time.monotonic()
                    elapsed = now - read_started_at
                    should_log = (
                        now - last_log_at >= RESPONSE_BODY_PROGRESS_INTERVAL_SECONDS
                        or new_bytes >= RESPONSE_BODY_PROGRESS_BYTES
                    )
                    if should_log:
                        AIClient._log_body_progress(url, received_bytes, content_length, elapsed)
                        last_log_at = now
                        last_log_bytes = received_bytes

                    should_callback = (
                        now - last_callback_at >= RESPONSE_BODY_PROGRESS_INTERVAL_SECONDS
                        or received_bytes - last_callback_bytes >= RESPONSE_BODY_PROGRESS_BYTES
                    )
                    if on_body_progress is not None and should_callback:
                        with suppress(Exception):
                            await on_body_progress(received_bytes, content_length, elapsed)
                        last_callback_at = now
                        last_callback_bytes = received_bytes

                if read_complete.is_set():
                    break

            response._content = b"".join(chunks)
            body_seconds = time.monotonic() - read_started_at
            if on_body_progress is not None:
                with suppress(Exception):
                    await on_body_progress(received_bytes, content_length, body_seconds)
            return body_seconds, received_bytes
        except asyncio.TimeoutError as exc:
            reader_task.cancel()
            with suppress(asyncio.CancelledError):
                await reader_task
            elapsed = time.monotonic() - read_started_at
            AIClient._log_body_progress(
                url,
                received_bytes,
                content_length,
                elapsed,
                timeout=True,
            )
            raise AIResponseBodyTimeoutError(
                (
                    f"AI response body from {url} was not fully received within "
                    f"{AI_RESPONSE_BODY_TIMEOUT}s ({received_bytes}/{content_length or '?'} bytes)"
                )
            ) from exc

    @staticmethod
    def _parse_content_length(value: str | None) -> int | None:
        if not value:
            return None
        try:
            length = int(value)
        except (TypeError, ValueError):
            return None
        return length if length >= 0 else None

    @staticmethod
    def _log_body_progress(
        url: str,
        received_bytes: int,
        content_length: int | None,
        elapsed_seconds: float,
        waiting: bool = False,
        timeout: bool = False,
    ) -> None:
        speed = received_bytes / elapsed_seconds if elapsed_seconds > 0 else 0.0
        total = str(content_length) if content_length is not None else "unknown"
        if timeout:
            logger.error(
                "[AI BODY TIMEOUT] %s | received=%s/%s bytes | elapsed=%.1fs | avg_speed=%.1f B/s",
                url,
                received_bytes,
                total,
                elapsed_seconds,
                speed,
            )
            return
        if waiting:
            logger.warning(
                "[AI BODY WAIT] %s | received=%s/%s bytes | elapsed=%.1fs | avg_speed=%.1f B/s",
                url,
                received_bytes,
                total,
                elapsed_seconds,
                speed,
            )
            return
        logger.info(
            "[AI BODY PROGRESS] %s | received=%s/%s bytes | elapsed=%.1fs | avg_speed=%.1f B/s",
            url,
            received_bytes,
            total,
            elapsed_seconds,
            speed,
        )

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
    def _apply_response_format(payload: dict, api_config: ActiveApiConfig | None = None) -> None:
        response_format = api_config.response_format if api_config is not None else AI_IMAGE_RESPONSE_FORMAT
        api_url = api_config.api_url if api_config is not None else AI_API_URL
        if response_format not in {"url", "b64_json"}:
            return
        if not AIClient._supports_response_format(api_url):
            return
        payload["response_format"] = response_format

    @staticmethod
    def _apply_provider_payload_options(payload: dict, api_config: ActiveApiConfig | None = None) -> None:
        if api_config is not None and not api_config.send_quality:
            payload.pop("quality", None)

    @staticmethod
    def _supports_response_format(api_url: str) -> bool:
        host = (urlparse(api_url).hostname or "").lower()
        return host not in RESPONSE_FORMAT_UNSUPPORTED_HOSTS

    @staticmethod
    def _remove_response_format(payload: dict) -> bool:
        return payload.pop("response_format", None) is not None

    @staticmethod
    def _summarize_request_payload(payload: dict) -> str:
        safe_payload = {
            "model": payload.get("model"),
            "size": payload.get("size"),
            "quality": payload.get("quality"),
            "n": payload.get("n"),
            "response_format": payload.get("response_format"),
        }
        return ", ".join(f"{key}={value}" for key, value in safe_payload.items() if value not in (None, ""))

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
            if response.status_code == 402 and AIClient._is_insufficient_credits_error(detail):
                raise AIInsufficientCreditsError("上游 API Key 余额不足，请在管理员控制台更换或充值 API Key。")
            if response.status_code in {401, 403}:
                raise AIAuthenticationError("上游 API Key 认证失败，请在管理员控制台更换或检查 API Key。")
            if response.status_code == 400 and AIClient._is_unsupported_response_format_error(detail):
                raise AIUnsupportedParameterError(
                    "上游图片接口不支持 response_format 参数，任务已停止并退款；"
                    "当前平台无法通过 URL 响应规避大图传输中断，请关闭 AI_IMAGE_RESPONSE_FORMAT 或更换支持 URL 返回的接口。"
                )
            if 500 <= response.status_code <= 599:
                raise AIUpstreamServerError(
                    f"上游生成服务暂时异常（HTTP {response.status_code}），任务已退款，请稍后重试或切换 API 通道。"
                )
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
    def _is_insufficient_credits_error(detail: str) -> bool:
        normalized = detail.lower()
        return "insufficient_credits" in normalized or (
            "no remaining credits" in normalized
            or ("insufficient" in normalized and "credit" in normalized)
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
        data_url, image_url = await AIClient._extract_image_result(response, client)
        return image_url or data_url

    @staticmethod
    async def _extract_image_result_with_timeout(
        response: httpx.Response,
        client: httpx.AsyncClient,
    ) -> tuple[str, str | None]:
        try:
            return await asyncio.wait_for(
                AIClient._extract_image_result(response, client),
                timeout=AI_RESPONSE_BODY_TIMEOUT,
            )
        except asyncio.TimeoutError as exc:
            raise AIResponseBodyTimeoutError(
                f"AI response body was not fully received within {AI_RESPONSE_BODY_TIMEOUT}s"
            ) from exc

    @staticmethod
    async def _extract_image_result(response: httpx.Response, client: httpx.AsyncClient) -> tuple[str, str | None]:
        content_type = AIClient._normalize_mime_type(response.headers.get("content-type"))
        if content_type or AIClient._guess_mime_type(response.content):
            return AIClient._bytes_to_data_url(response.content, content_type), None

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
            return f"data:{mime_type or 'image/png'};base64,{b64_json}", None

        image_url = AIClient._extract_image_url(item)
        if image_url:
            if image_url.startswith("data:image/"):
                return image_url, None
            return "", image_url

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


class AIResponseInterruptedError(Exception):
    pass


class AIResponseBodyTimeoutError(Exception):
    pass


class AIKeyTerminalError(Exception):
    pass


class AIInsufficientCreditsError(AIKeyTerminalError):
    pass


class AIAuthenticationError(AIKeyTerminalError):
    pass


class AIRateLimitError(Exception):
    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class AIUnsupportedParameterError(Exception):
    pass


class AIUpstreamServerError(Exception):
    pass
