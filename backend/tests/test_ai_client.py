import base64
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services.ai_client import (
    AIClient,
    AIInsufficientCreditsError,
    AIResponseBodyTimeoutError,
    AIResponseInterruptedError,
    AIResponsePayloadError,
    AIUpstreamServerError,
    AIRateLimitError,
    AIUnsupportedParameterError,
)
from app.services.api_key_manager import ActiveApiConfig


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
)


class SlowBodyStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        import asyncio

        await asyncio.sleep(1)
        yield b"{}"


class ChunkedBodyStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


class AIClientResponseTest(unittest.IsolatedAsyncioTestCase):
    def api_config(
        self,
        api_url: str = "https://www.aiartmirror.com/v1",
        api_key: str = "test-key",
        response_format: str | None = None,
        send_quality: bool = True,
    ) -> ActiveApiConfig:
        return ActiveApiConfig(
            api_url=api_url,
            api_key=api_key,
            response_format=response_format,
            send_quality=send_quality,
            config_id=None,
            key_mask="test...key",
        )

    async def test_extracts_b64_json_response(self) -> None:
        response = httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
        )

        async with httpx.AsyncClient() as client:
            data_url = await AIClient._extract_image_data_url(response, client)

        self.assertTrue(data_url.startswith("data:image/png;base64,"))

    async def test_download_image_url_as_data_url_helper(self) -> None:
        image_url = "https://image.example/generated.png"

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), image_url)
            return httpx.Response(200, content=PNG_BYTES, headers={"content-type": "image/png"})

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(transport=transport) as client:
            data_url = await AIClient._download_image_as_data_url(client, image_url)

        self.assertEqual(
            data_url,
            f"data:image/png;base64,{base64.b64encode(PNG_BYTES).decode('ascii')}",
        )

    async def test_extracts_remote_url_without_backend_download(self) -> None:
        image_url = "https://image.example/generated.png"
        response = httpx.Response(200, json={"data": [{"url": image_url}]})

        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("remote image should not be downloaded before task completion")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            data_url, remote_url = await AIClient._extract_image_result(response, client)

        self.assertEqual(data_url, "")
        self.assertEqual(remote_url, image_url)

    async def test_public_extract_returns_remote_url_for_url_response(self) -> None:
        image_url = "https://image.example/generated.png"
        response = httpx.Response(200, json={"data": [{"url": image_url}]})

        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("remote image should not be downloaded by compatibility extractor")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            data_url = await AIClient._extract_image_data_url(response, client)

        self.assertEqual(data_url, image_url)

    async def test_download_helper_rejects_response_when_download_is_not_image(self) -> None:
        image_url = "https://image.example/error"
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, text="<html>error</html>", headers={"content-type": "text/html"})
        )

        async with httpx.AsyncClient(transport=transport) as client:
            with self.assertRaises(AIResponsePayloadError):
                await AIClient._download_image_as_data_url(client, image_url)

    async def test_extract_returns_remote_url_even_when_download_would_fail(self) -> None:
        image_url = "https://image.example/generated.png"
        response = httpx.Response(200, json={"data": [{"url": image_url}]})
        transport = httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("network blocked", request=request))
        )

        async with httpx.AsyncClient(transport=transport) as client:
            data_url = await AIClient._extract_image_data_url(response, client)

        self.assertEqual(data_url, image_url)

    async def test_call_api_returns_remote_url_for_url_response(self) -> None:
        image_url = "https://image.example/generated.png"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": [{"url": image_url}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
            ):
                data_url = await AIClient._call_api("https://api.example/v1/images/generations", {})

        self.assertEqual(data_url, image_url)

    async def test_generate_does_not_request_response_format_by_default(self) -> None:
        seen_payload = {}

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal seen_payload
            seen_payload = json.loads(request.read().decode("utf-8"))
            return httpx.Response(
                200,
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config()),
                ),
            ):
                result = await AIClient.generate_with_metadata("prompt text", "high", "2304x3072")

        self.assertNotIn("response_format", seen_payload)
        self.assertIsNone(result.image_url)
        self.assertIsNone(result.request_response_format)

    async def test_generate_requests_url_response_when_configured(self) -> None:
        seen_payload = {}
        image_url = "https://image.example/generated.png"

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal seen_payload
            seen_payload = json.loads(request.read().decode("utf-8"))
            return httpx.Response(200, json={"data": [{"url": image_url}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config("https://api.example/v1", response_format="url")),
                ),
            ):
                result = await AIClient.generate_with_metadata("prompt text", "high", "2304x3072")

        self.assertEqual(seen_payload["response_format"], "url")
        self.assertEqual(result.image_url, image_url)
        self.assertEqual(result.request_response_format, "url")

    async def test_generate_uses_active_api_config_authorization(self) -> None:
        seen_auth = ""

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal seen_auth
            seen_auth = request.headers.get("authorization", "")
            return httpx.Response(
                200,
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config("https://api.example/v1", "runtime-key")),
                ),
            ):
                await AIClient.generate_with_metadata("prompt text", "low", "1024x1024")

        self.assertEqual(seen_auth, "Bearer runtime-key")

    async def test_aiartmirror_does_not_request_response_format_even_when_configured(self) -> None:
        seen_payload = {}

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal seen_payload
            seen_payload = json.loads(request.read().decode("utf-8"))
            return httpx.Response(
                200,
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config(response_format="url")),
                ),
            ):
                result = await AIClient.generate_with_metadata("prompt text", "high", "2304x3072")

        self.assertNotIn("response_format", seen_payload)
        self.assertIsNone(result.request_response_format)

    async def test_generate_can_omit_quality_for_provider_compatibility(self) -> None:
        seen_payload = {}

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal seen_payload
            seen_payload = json.loads(request.read().decode("utf-8"))
            return httpx.Response(
                200,
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config("https://api.zilan520.shop/v1", send_quality=False)),
                ),
            ):
                result = await AIClient.generate_with_metadata("prompt text", "high", "2160x3840")

        self.assertEqual(seen_payload["size"], "2160x3840")
        self.assertNotIn("quality", seen_payload)
        self.assertEqual(result.request_quality, "")

    async def test_5xx_marks_key_failed_and_returns_sanitized_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                502,
                json={
                    "error": {
                        "message": "An error occurred. Include request ID secret-request-id."
                    }
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config("https://api.zilan520.shop/v1")),
                ),
                patch("app.services.ai_client.mark_api_config_failed", new=AsyncMock()) as mark_failed,
            ):
                with self.assertRaises(AIUpstreamServerError) as ctx:
                    await AIClient.generate_with_metadata("prompt text", "high", "2160x3840")

        self.assertIn("HTTP 502", str(ctx.exception))
        self.assertNotIn("secret-request-id", str(ctx.exception))
        mark_failed.assert_awaited_once()

    async def test_remote_protocol_error_is_reported_as_response_interrupted(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.RemoteProtocolError(
                "peer closed connection without sending complete message body",
                request=request,
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config()),
                ),
            ):
                with self.assertRaises(AIResponseInterruptedError) as ctx:
                    await AIClient.generate_with_metadata("prompt text", "high", "2304x3072")

        self.assertIn("响应传输中断", str(ctx.exception))

    def test_parses_rate_limit_delay_from_error_message(self) -> None:
        response = httpx.Response(
            429,
            json={
                "error": {
                    "message": (
                        "Rate limit reached for gpt-image-2 on input-images per min: "
                        "Limit 250, Used 250, Requested 1. Please try again in 240ms."
                    )
                }
            },
        )

        with self.assertRaises(AIRateLimitError) as ctx:
            AIClient._handle_response(response, "https://api.example/v1/images/generations")

        self.assertAlmostEqual(ctx.exception.retry_after_seconds, 0.24)

    def test_prefers_retry_after_header_for_rate_limit_delay(self) -> None:
        response = httpx.Response(
            429,
            headers={"retry-after": "1.5"},
            json={"error": {"message": "Rate limited"}},
        )

        with self.assertRaises(AIRateLimitError) as ctx:
            AIClient._handle_response(response, "https://api.example/v1/images/generations")

        self.assertEqual(ctx.exception.retry_after_seconds, 1.5)

    def test_raises_insufficient_credits_for_402(self) -> None:
        response = httpx.Response(
            402,
            json={
                "error": {
                    "message": "[402 insufficient_credits] token tk_example has no remaining credits"
                }
            },
        )

        with self.assertRaises(AIInsufficientCreditsError) as ctx:
            AIClient._handle_response(response, "https://api.example/v1/images/generations")

        self.assertIn("余额不足", str(ctx.exception))
        self.assertNotIn("tk_example", str(ctx.exception))

    async def test_generate_fails_over_to_backup_key_on_insufficient_credits(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.headers.get("authorization", ""))
            if len(calls) == 1:
                return httpx.Response(
                    402,
                    json={"error": {"message": "[402 insufficient_credits] token tk_example has no remaining credits"}},
                )
            return httpx.Response(
                200,
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        primary = ActiveApiConfig(
            api_url="https://api.example/v1",
            api_key="primary-key",
            response_format=None,
            config_id=1,
            key_mask="primary",
        )
        backup = ActiveApiConfig(
            api_url="https://api.example/v1",
            api_key="backup-key",
            response_format=None,
            config_id=2,
            key_mask="backup",
        )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch("app.services.ai_client.get_active_api_config", new=AsyncMock(side_effect=[primary, backup])),
                patch("app.services.ai_client.mark_api_config_failed", new=AsyncMock()) as mark_failed,
                patch("app.services.ai_client.invalidate_active_api_config_cache") as invalidate,
                patch("app.services.ai_client.touch_api_config_used", new=AsyncMock()),
            ):
                result = await AIClient.generate_with_metadata("prompt text", "low", "1024x1024")

        self.assertTrue(result.data_url.startswith("data:image/png;base64,"))
        self.assertEqual(calls, ["Bearer primary-key", "Bearer backup-key"])
        mark_failed.assert_awaited_once()
        invalidate.assert_called()

    def test_rate_limit_retry_delay_uses_local_minimum(self) -> None:
        with patch("app.services.ai_client.random.uniform", return_value=0):
            self.assertGreaterEqual(AIClient._retry_delay(0.24, 0), 2.0)

    async def test_retries_rate_limited_request_until_success(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(
                    429,
                    json={"error": {"message": "Rate limited. Please try again in 240ms."}},
                )
            return httpx.Response(
                200,
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch("app.services.ai_client.asyncio.sleep", new=AsyncMock()),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch("app.services.ai_client.random.uniform", return_value=0),
            ):
                data_url = await AIClient._call_api("https://api.example/v1/images/generations", {})

        self.assertTrue(data_url.startswith("data:image/png;base64,"))
        self.assertEqual(calls, 2)

    async def test_rejects_unsupported_response_format_without_fallback(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(
                400,
                json={"error": {"message": "Invalid parameter: response_format is not supported"}},
            )

        payload = {"model": "gpt-image-2", "prompt": "x", "response_format": "url"}
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
            ):
                with self.assertRaises(AIUnsupportedParameterError):
                    await AIClient._call_api("https://api.example/v1/images/generations", payload)

        self.assertEqual(calls, 1)
        self.assertIn("response_format", payload)

    async def test_retries_without_response_format_when_fallback_is_enabled(self) -> None:
        payloads = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = request.read().decode("utf-8")
            payloads.append(payload)
            if len(payloads) == 1:
                return httpx.Response(
                    400,
                    json={"error": {"message": "Invalid parameter: response_format is not supported"}},
                )
            return httpx.Response(
                200,
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        payload = {"model": "gpt-image-2", "prompt": "x", "response_format": "url"}
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch("app.services.ai_client.AI_RESPONSE_FORMAT_FALLBACK", True),
            ):
                data_url = await AIClient._call_api("https://api.example/v1/images/generations", payload)

        self.assertTrue(data_url.startswith("data:image/png;base64,"))
        self.assertIn("response_format", payloads[0])
        self.assertNotIn("response_format", payloads[1])

    async def test_unknown_response_format_parameter_is_not_retried_by_default(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(
                400,
                json={"error": {"message": "Unknown parameter: 'response_format'."}},
            )

        payload = {"model": "gpt-image-2", "prompt": "x", "response_format": "url"}
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
            ):
                with self.assertRaises(AIUnsupportedParameterError):
                    await AIClient._call_api("https://api.example/v1/images/generations", payload)

        self.assertEqual(calls, 1)
        self.assertIn("response_format", payload)

    async def test_edit_sends_detected_upload_mime_type(self) -> None:
        seen_body = b""

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal seen_body
            seen_body = request.read()
            return httpx.Response(
                200,
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config()),
                ),
            ):
                data_url = await AIClient.edit(
                    b"\xff\xd8\xffjpeg",
                    "edit prompt",
                    "low",
                    "1024x1024",
                    "image.jpg",
                    "image/jpeg",
                )

        self.assertTrue(data_url.startswith("data:image/png;base64,"))
        self.assertIn(b'filename="image.jpg"', seen_body)
        self.assertIn(b"Content-Type: image/jpeg", seen_body)

    async def test_generate_returns_safe_request_metadata(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={
                    "content-type": "application/json",
                    "x-request-id": "req_test_123",
                },
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config()),
                ),
            ):
                result = await AIClient.generate_with_metadata("prompt text", "high", "1024x1024")

        self.assertTrue(result.data_url.startswith("data:image/png;base64,"))
        self.assertEqual(result.model, "gpt-image-2")
        self.assertEqual(result.endpoint, "/v1/images/generations")
        self.assertEqual(result.request_quality, "high")
        self.assertEqual(result.request_size, "1024x1024")
        self.assertEqual(result.response_request_id, "req_test_123")
        self.assertIsNone(result.request_response_format)

    async def test_response_headers_callback_runs_before_body_parsing(self) -> None:
        seen_headers = {}

        async def on_response_headers(response: httpx.Response) -> None:
            seen_headers["request_id"] = response.headers.get("x-request-id")
            seen_headers["content_type"] = response.headers.get("content-type")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={
                    "content-type": "application/json",
                    "x-request-id": "req_headers_123",
                },
                json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.ai_client.get_client", new=AsyncMock(return_value=client)),
                patch.object(AIClient, "_wait_for_request_slot", new=AsyncMock()),
                patch(
                    "app.services.ai_client.get_active_api_config",
                    new=AsyncMock(return_value=self.api_config()),
                ),
            ):
                result = await AIClient.generate_with_metadata(
                    "prompt text",
                    "high",
                    "1024x1024",
                    on_response_headers=on_response_headers,
                )

        self.assertTrue(result.data_url.startswith("data:image/png;base64,"))
        self.assertEqual(seen_headers["request_id"], "req_headers_123")
        self.assertEqual(seen_headers["content_type"], "application/json")

    async def test_response_body_read_timeout_is_reported(self) -> None:
        response = httpx.Response(200, stream=SlowBodyStream())

        with patch("app.services.ai_client.AI_RESPONSE_BODY_TIMEOUT", 0.01):
            with self.assertRaises(AIResponseBodyTimeoutError):
                await AIClient._read_response_body_with_timeout(response, "https://api.example/v1/images/generations")

    async def test_response_body_read_preserves_chunked_content_for_json_parse(self) -> None:
        body = json.dumps({"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]}).encode("utf-8")
        response = httpx.Response(
            200,
            headers={"content-length": str(len(body)), "content-type": "application/json"},
            stream=ChunkedBodyStream([body[:12], body[12:28], body[28:]]),
        )

        seen_progress = []

        async def on_progress(received_bytes, total_bytes, elapsed_seconds):
            seen_progress.append((received_bytes, total_bytes, elapsed_seconds))

        body_seconds, body_bytes = await AIClient._read_response_body_with_timeout(
            response,
            "https://api.example/v1/images/generations",
            on_body_progress=on_progress,
        )

        self.assertGreaterEqual(body_seconds, 0)
        self.assertEqual(body_bytes, len(body))
        self.assertEqual(response.json()["data"][0]["b64_json"], base64.b64encode(PNG_BYTES).decode("ascii"))
        self.assertEqual(seen_progress[-1][0], len(body))
        self.assertEqual(seen_progress[-1][1], len(body))

    async def test_response_body_timeout_reports_received_bytes(self) -> None:
        response = httpx.Response(
            200,
            headers={"content-length": "100"},
            stream=SlowBodyStream(),
        )

        with patch("app.services.ai_client.AI_RESPONSE_BODY_TIMEOUT", 0.01):
            with self.assertRaises(AIResponseBodyTimeoutError) as ctx:
                await AIClient._read_response_body_with_timeout(response, "https://api.example/v1/images/generations")

        self.assertIn("0/100 bytes", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
