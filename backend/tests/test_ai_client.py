import base64
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services.ai_client import AIClient, AIResponsePayloadError, AIRateLimitError


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
)


class AIClientResponseTest(unittest.IsolatedAsyncioTestCase):
    async def test_extracts_b64_json_response(self) -> None:
        response = httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
        )

        async with httpx.AsyncClient() as client:
            data_url = await AIClient._extract_image_data_url(response, client)

        self.assertTrue(data_url.startswith("data:image/png;base64,"))

    async def test_downloads_url_response_as_data_url(self) -> None:
        image_url = "https://image.example/generated.png"

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), image_url)
            return httpx.Response(200, content=PNG_BYTES, headers={"content-type": "image/png"})

        response = httpx.Response(200, json={"data": [{"url": image_url}]})
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(transport=transport) as client:
            data_url = await AIClient._extract_image_data_url(response, client)

        self.assertEqual(
            data_url,
            f"data:image/png;base64,{base64.b64encode(PNG_BYTES).decode('ascii')}",
        )

    async def test_rejects_url_response_when_download_is_not_image(self) -> None:
        response = httpx.Response(200, json={"data": [{"url": "https://image.example/error"}]})
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, text="<html>error</html>", headers={"content-type": "text/html"})
        )

        async with httpx.AsyncClient(transport=transport) as client:
            with self.assertRaises(AIResponsePayloadError):
                await AIClient._extract_image_data_url(response, client)

    async def test_falls_back_to_remote_url_when_download_fails(self) -> None:
        image_url = "https://image.example/generated.png"
        response = httpx.Response(200, json={"data": [{"url": image_url}]})
        transport = httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("network blocked", request=request))
        )

        async with httpx.AsyncClient(transport=transport) as client:
            data_url = await AIClient._extract_image_data_url(response, client)

        self.assertEqual(data_url, image_url)

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

    async def test_retries_without_response_format_when_provider_rejects_it(self) -> None:
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
            ):
                data_url = await AIClient._call_api("https://api.example/v1/images/generations", payload)

        self.assertTrue(data_url.startswith("data:image/png;base64,"))
        self.assertIn("response_format", payloads[0])
        self.assertNotIn("response_format", payloads[1])

    async def test_retries_without_response_format_for_unknown_parameter_error(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(
                    400,
                    json={"error": {"message": "Unknown parameter: 'response_format'."}},
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
            ):
                data_url = await AIClient._call_api("https://api.example/v1/images/generations", payload)

        self.assertTrue(data_url.startswith("data:image/png;base64,"))
        self.assertEqual(calls, 2)
        self.assertNotIn("response_format", payload)

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
            ):
                result = await AIClient.generate_with_metadata("prompt text", "high", "1024x1024")

        self.assertTrue(result.data_url.startswith("data:image/png;base64,"))
        self.assertEqual(result.model, "gpt-image-2")
        self.assertEqual(result.endpoint, "/v1/images/generations")
        self.assertEqual(result.request_quality, "high")
        self.assertEqual(result.request_size, "1024x1024")
        self.assertEqual(result.response_request_id, "req_test_123")
        self.assertIsNone(result.request_response_format)


if __name__ == "__main__":
    unittest.main()
