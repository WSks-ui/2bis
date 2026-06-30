import unittest
import json
from datetime import datetime, timedelta
from types import ModuleType
from unittest.mock import AsyncMock, patch
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.modules.setdefault("boto3", ModuleType("boto3"))
redis_module = sys.modules.setdefault("redis", ModuleType("redis"))
redis_asyncio_module = sys.modules.setdefault("redis.asyncio", ModuleType("redis.asyncio"))
setattr(redis_asyncio_module, "Redis", object)
setattr(redis_module, "asyncio", redis_asyncio_module)
import worker
from app.database import Base
from app.models import GenerateHistory, GenerationTask, GenerationTaskStatus, User
from app.services.ai_client import (
    AIImageResult,
    AIInsufficientCreditsError,
    AINoAvailableApiConfigError,
    AIResponseBodyTimeoutError,
    AIResponseInterruptedError,
    AIUpstreamServerError,
    AIUnsupportedParameterError,
    AIUsageLimitError,
)


class WorkerRecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session_patch = patch.object(worker, "async_session", self.session_factory)
        self.session_patch.start()

    async def asyncTearDown(self) -> None:
        self.session_patch.stop()
        await self.engine.dispose()

    async def test_read_task_source_images_uses_multiple_saved_images(self) -> None:
        task = GenerationTask(
            source_image_paths=json.dumps(["a.png", "b.jpg", "c.webp"]),
            source_image_mime_types=json.dumps(["image/png", "image/jpeg", "image/webp"]),
        )

        async def fake_read(path: str) -> bytes:
            return path.encode("utf-8")

        with patch.object(worker, "read_upload_file", side_effect=fake_read):
            images = await worker.read_task_source_images(task)

        self.assertEqual(
            images,
            [
                (b"a.png", "image-1.png", "image/png"),
                (b"b.jpg", "image-2.jpg", "image/jpeg"),
                (b"c.webp", "image-3.webp", "image/webp"),
            ],
        )

    async def test_read_task_source_images_falls_back_to_legacy_single_image(self) -> None:
        task = GenerationTask(
            source_image_path="legacy.jpg",
            source_image_mime_type="image/jpeg",
        )

        async def fake_read(path: str) -> bytes:
            return path.encode("utf-8")

        with patch.object(worker, "read_upload_file", side_effect=fake_read):
            images = await worker.read_task_source_images(task)

        self.assertEqual(images, [(b"legacy.jpg", "image-1.jpg", "image/jpeg")])

    async def test_read_task_source_mask_uses_saved_mask(self) -> None:
        task = GenerationTask(
            source_mask_path="mask.png",
            source_mask_mime_type="image/png",
        )

        async def fake_read(path: str) -> bytes:
            return path.encode("utf-8")

        with patch.object(worker, "read_upload_file", side_effect=fake_read):
            mask = await worker.read_task_source_mask(task)

        self.assertEqual(mask, (b"mask.png", "mask.png", "image/png"))

    async def test_stale_processing_task_is_refunded_without_requeue(self) -> None:
        async with self.session_factory() as db:
            user = User(
                username="stale-user",
                hashed_password="x",
                monthly_quota_total=10,
                monthly_quota_remaining=7,
            )
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                status=GenerationTaskStatus.PROCESSING,
                points_cost=3,
                balance_source="quota",
                locked_at=datetime.utcnow() - timedelta(hours=2),
                retry_count=2,
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with patch.object(worker, "enqueue_generation_task", autospec=True) as enqueue:
            await worker.recover_stale_processing_tasks()

        enqueue.assert_not_called()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.REFUNDED)
        self.assertIsNone(task.locked_at)
        self.assertIsNotNone(task.finished_at)
        self.assertIn("quota has been refunded", task.error_message)
        self.assertEqual(user.monthly_quota_remaining, 10)

    async def test_remote_url_result_marks_task_success_without_blocking_download(self) -> None:
        remote_url = "https://image.example/generated.png"
        ai_result = AIImageResult(
            data_url="",
            image_url=remote_url,
            model="gpt-image-2",
            endpoint="/v1/images/generations",
            request_quality="low",
            request_size="1024x1024",
            request_response_format="url",
            response_request_id="req_remote",
            response_content_type="application/json",
            elapsed_seconds=180.0,
            header_seconds=159.0,
            body_seconds=20.5,
            parse_seconds=0.25,
            body_bytes=15425302,
            content_length=15425302,
            transfer_encoding="chunked",
            payload_length=len(remote_url),
        )

        async with self.session_factory() as db:
            user = User(username="remote-user", hashed_password="x")
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="fast result",
                quality="low",
                size="1024x1024",
                points_cost=1,
                balance_source="free_points",
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(worker.AIClient, "generate_with_metadata", new=AsyncMock(return_value=ai_result)),
            patch.object(worker, "save_data_url", new=AsyncMock(side_effect=AssertionError("remote URL must not block success"))),
            patch.object(worker, "schedule_remote_image_mirror") as schedule_mirror,
        ):
            await worker.process_task(task_id)

        schedule_mirror.assert_called_once_with(task_id, user_id, remote_url)

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            result = await db.execute(select(GenerateHistory).where(GenerateHistory.task_id == task_id))
            history = result.scalar_one()

        self.assertEqual(task.status, GenerationTaskStatus.SUCCESS)
        self.assertEqual(task.image_url, remote_url)
        self.assertIsNotNone(task.finished_at)
        self.assertEqual(task.upstream_elapsed_seconds, 180.0)
        self.assertEqual(task.upstream_header_seconds, 159.0)
        self.assertEqual(task.upstream_body_seconds, 20.5)
        self.assertEqual(task.upstream_parse_seconds, 0.25)
        self.assertIsNotNone(task.upstream_save_seconds)
        self.assertLess(task.upstream_save_seconds, 1.0)
        self.assertEqual(task.upstream_body_bytes, 15425302)
        self.assertEqual(task.upstream_content_length, 15425302)
        self.assertEqual(task.upstream_transfer_encoding, "chunked")
        self.assertEqual(task.upstream_response_format, "url")
        self.assertEqual(history.user_id, user_id)
        self.assertEqual(history.image_url, remote_url)
        self.assertEqual(history.upstream_body_seconds, 20.5)
        self.assertIsNotNone(history.upstream_save_seconds)

    async def test_masked_edit_task_calls_ai_client_with_mask(self) -> None:
        ai_result = AIImageResult(
            data_url="data:image/png;base64,abc",
            image_url=None,
            model="gpt-image-2",
            endpoint="/v1/images/edits",
            request_quality="low",
            request_size="1024x1024",
            request_response_format=None,
            response_request_id="req_mask",
            response_content_type="application/json",
            elapsed_seconds=3.0,
            payload_length=25,
        )

        async with self.session_factory() as db:
            user = User(username="masked-edit-user", hashed_password="x")
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="edit selected area",
                mode="edit",
                quality="low",
                size="1024x1024",
                points_cost=1,
                balance_source="free_points",
                source_image_paths=json.dumps(["source.png"]),
                source_image_mime_types=json.dumps(["image/png"]),
                source_mask_path="mask.png",
                source_mask_mime_type="image/png",
            )
            db.add(task)
            await db.commit()
            task_id = task.id

        async def fake_read(path: str) -> bytes:
            return path.encode("utf-8")

        mask_edit = AsyncMock(return_value=ai_result)
        with (
            patch.object(worker, "read_upload_file", side_effect=fake_read),
            patch.object(worker.AIClient, "edit_with_mask_metadata", new=mask_edit),
            patch.object(worker.AIClient, "edit_multiple_with_metadata", new=AsyncMock()) as multi_edit,
            patch.object(worker, "save_data_url", new=AsyncMock(return_value="/static/images/1/masked.png")),
        ):
            await worker.process_task(task_id)

        mask_edit.assert_awaited_once()
        image_arg, mask_arg = mask_edit.await_args.args[:2]
        self.assertEqual(image_arg, (b"source.png", "image-1.png", "image/png"))
        self.assertEqual(mask_arg, (b"mask.png", "mask.png", "image/png"))
        multi_edit.assert_not_awaited()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)

        self.assertEqual(task.status, GenerationTaskStatus.SUCCESS)
        self.assertEqual(task.image_url, "/static/images/1/masked.png")

    async def test_remote_image_mirror_updates_task_and_history_to_local_url(self) -> None:
        remote_url = "https://image.example/generated.png"
        local_url = "/static/images/1/local.png"

        async with self.session_factory() as db:
            user = User(username="mirror-user", hashed_password="x")
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="mirror result",
                status=GenerationTaskStatus.SUCCESS,
                image_url=remote_url,
            )
            db.add(task)
            await db.flush()
            history = GenerateHistory(
                user_id=user.id,
                task_id=task.id,
                prompt=task.prompt,
                image_url=remote_url,
                quality=task.quality,
                points_cost=task.points_cost,
            )
            db.add(history)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(worker, "get_client", new=AsyncMock(return_value=object())),
            patch.object(worker.AIClient, "_download_image_as_data_url", new=AsyncMock(return_value="data:image/png;base64,abc")),
            patch.object(worker, "save_data_url", new=AsyncMock(return_value=local_url)),
        ):
            await worker.mirror_remote_image(task_id, user_id, remote_url)

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            result = await db.execute(select(GenerateHistory).where(GenerateHistory.task_id == task_id))
            history = result.scalar_one()

        self.assertEqual(task.image_url, local_url)
        self.assertEqual(history.image_url, local_url)

    async def test_interrupted_upstream_response_is_not_requeued(self) -> None:
        async with self.session_factory() as db:
            user = User(username="interrupted-user", hashed_password="x", monthly_quota_total=3, monthly_quota_remaining=2)
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                quality="high",
                size="2304x3072",
                points_cost=1,
                balance_source="quota",
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(
                worker.AIClient,
                "generate_with_metadata",
                new=AsyncMock(side_effect=AIResponseInterruptedError("response interrupted")),
            ),
            patch.object(worker, "enqueue_generation_task", new=AsyncMock()) as enqueue,
        ):
            await worker.process_task(task_id)

        enqueue.assert_not_awaited()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.REFUNDED)
        self.assertEqual(task.retry_count, 1)
        self.assertIn("response interrupted", task.error_message)
        self.assertEqual(user.monthly_quota_remaining, 3)

    async def test_unsupported_response_format_is_refunded_without_requeue(self) -> None:
        message = "上游图片接口不支持 response_format 参数"
        async with self.session_factory() as db:
            user = User(username="unsupported-format-user", hashed_password="x", monthly_quota_total=3, monthly_quota_remaining=2)
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                quality="high",
                size="2304x3072",
                points_cost=1,
                balance_source="quota",
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(
                worker.AIClient,
                "generate_with_metadata",
                new=AsyncMock(side_effect=AIUnsupportedParameterError(message)),
            ),
            patch.object(worker, "enqueue_generation_task", new=AsyncMock()) as enqueue,
        ):
            await worker.process_task(task_id)

        enqueue.assert_not_awaited()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.REFUNDED)
        self.assertEqual(task.retry_count, 1)
        self.assertIn("response_format", task.error_message)
        self.assertEqual(user.monthly_quota_remaining, 3)

    async def test_response_body_timeout_is_refunded_without_requeue(self) -> None:
        message = "AI response body was not fully received within 180s"
        async with self.session_factory() as db:
            user = User(username="body-timeout-user", hashed_password="x", monthly_quota_total=3, monthly_quota_remaining=2)
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                quality="high",
                size="2304x3072",
                points_cost=1,
                balance_source="quota",
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(
                worker.AIClient,
                "generate_with_metadata",
                new=AsyncMock(side_effect=AIResponseBodyTimeoutError(message)),
            ),
            patch.object(worker, "enqueue_generation_task", new=AsyncMock()) as enqueue,
        ):
            await worker.process_task(task_id)

        enqueue.assert_not_awaited()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.REFUNDED)
        self.assertEqual(task.retry_count, 1)
        self.assertEqual(task.progress_stage, "failed")
        self.assertIn("fully received", task.error_message)
        self.assertEqual(user.monthly_quota_remaining, 3)

    async def test_insufficient_upstream_credits_is_refunded_without_requeue(self) -> None:
        message = "上游 API Key 余额不足，请在管理员控制台更换或充值 API Key。"
        async with self.session_factory() as db:
            user = User(username="upstream-credit-user", hashed_password="x", monthly_quota_total=3, monthly_quota_remaining=2)
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                quality="high",
                size="2304x3072",
                points_cost=1,
                balance_source="quota",
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(
                worker.AIClient,
                "generate_with_metadata",
                new=AsyncMock(side_effect=AIInsufficientCreditsError(message)),
            ),
            patch.object(worker, "enqueue_generation_task", new=AsyncMock()) as enqueue,
        ):
            await worker.process_task(task_id)

        enqueue.assert_not_awaited()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.REFUNDED)
        self.assertEqual(task.retry_count, 1)
        self.assertEqual(task.progress_stage, "failed")
        self.assertIn("余额不足", task.error_message)
        self.assertEqual(user.monthly_quota_remaining, 3)

    async def test_usage_limit_is_refunded_without_requeue_and_writes_audit_fields(self) -> None:
        usage_error = AIUsageLimitError(
            '{"code":"USAGE_LIMIT_EXCEEDED","reason":"DAILY_LIMIT_EXCEEDED","message":"daily usage limit exceeded"}',
            status_code=429,
            request_id="req_daily_limit",
            endpoint="/v1/images/generations",
            request_quality="high",
            request_size="2160x3840",
            content_type="application/json",
            elapsed_seconds=18.5,
            header_seconds=18.3,
            body_seconds=0.0,
            body_bytes=188,
            content_length=188,
            detail="daily usage limit exceeded",
        )
        async with self.session_factory() as db:
            user = User(username="usage-limit-user", hashed_password="x", monthly_quota_total=3, monthly_quota_remaining=2)
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                quality="high",
                size="2160x3840",
                points_cost=1,
                balance_source="quota",
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(
                worker.AIClient,
                "generate_with_metadata",
                new=AsyncMock(side_effect=usage_error),
            ),
            patch.object(worker, "enqueue_generation_task", new=AsyncMock()) as enqueue,
        ):
            await worker.process_task(task_id)

        enqueue.assert_not_awaited()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.REFUNDED)
        self.assertEqual(task.retry_count, 1)
        self.assertEqual(task.progress_stage, "failed")
        self.assertIn("DAILY_LIMIT_EXCEEDED", task.error_message)
        self.assertIn("request_id=req_daily_limit", task.error_message)
        self.assertEqual(task.upstream_endpoint, "/v1/images/generations")
        self.assertEqual(task.upstream_request_id, "req_daily_limit")
        self.assertEqual(task.upstream_elapsed_seconds, 18.5)
        self.assertEqual(task.upstream_header_seconds, 18.3)
        self.assertEqual(task.upstream_body_bytes, 188)
        self.assertEqual(task.upstream_content_length, 188)
        self.assertEqual(user.monthly_quota_remaining, 3)

    async def test_no_available_api_config_is_refunded_without_requeue(self) -> None:
        message = "没有可用的数据库 API 通道，且已禁止回退到 .env API Key。"
        async with self.session_factory() as db:
            user = User(username="no-api-config-user", hashed_password="x", monthly_quota_total=3, monthly_quota_remaining=2)
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                quality="high",
                size="2160x3840",
                points_cost=1,
                balance_source="quota",
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(
                worker.AIClient,
                "generate_with_metadata",
                new=AsyncMock(side_effect=AINoAvailableApiConfigError(message)),
            ),
            patch.object(worker, "enqueue_generation_task", new=AsyncMock()) as enqueue,
        ):
            await worker.process_task(task_id)

        enqueue.assert_not_awaited()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.REFUNDED)
        self.assertEqual(task.retry_count, 1)
        self.assertEqual(task.progress_stage, "failed")
        self.assertIn("没有可用", task.error_message)
        self.assertEqual(user.monthly_quota_remaining, 3)

    async def test_upstream_server_error_is_requeued_before_retry_limit(self) -> None:
        message = "上游生成服务暂时异常（HTTP 502），任务已退款，请稍后重试或切换 API 通道。"
        async with self.session_factory() as db:
            user = User(username="upstream-502-user", hashed_password="x", monthly_quota_total=3, monthly_quota_remaining=2)
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                quality="high",
                size="2160x3840",
                points_cost=1,
                balance_source="quota",
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(
                worker.AIClient,
                "generate_with_metadata",
                new=AsyncMock(side_effect=AIUpstreamServerError(message)),
            ),
            patch.object(worker, "enqueue_generation_task", new=AsyncMock()) as enqueue,
        ):
            await worker.process_task(task_id)

        enqueue.assert_awaited_once_with(task_id)

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.PENDING)
        self.assertEqual(task.retry_count, 1)
        self.assertEqual(task.progress_stage, "retrying")
        self.assertIn("HTTP 502", task.error_message)
        self.assertEqual(user.monthly_quota_remaining, 2)

    async def test_structured_upstream_server_error_writes_audit_fields(self) -> None:
        upstream_error = AIUpstreamServerError(
            "上游生成服务暂时异常（HTTP 502），任务已退款，请稍后重试或切换 API 通道。",
            status_code=502,
            request_id="req_zilan_502",
            endpoint="/v1/images/generations",
            request_quality="",
            request_size="3840x2160",
            content_type="application/json; charset=utf-8",
            elapsed_seconds=68.2,
            header_seconds=67.8,
            body_seconds=0.0,
            body_bytes=308,
            content_length=308,
            transfer_encoding=None,
            detail="bad gateway",
        )
        async with self.session_factory() as db:
            user = User(username="upstream-audit-user", hashed_password="x", monthly_quota_total=3, monthly_quota_remaining=2)
            db.add(user)
            await db.flush()
            task = GenerationTask(
                user_id=user.id,
                prompt="large image",
                quality="high",
                size="3840x2160",
                points_cost=1,
                balance_source="quota",
                retry_count=2,
                max_retries=2,
            )
            db.add(task)
            await db.commit()
            task_id = task.id
            user_id = user.id

        with (
            patch.object(
                worker.AIClient,
                "generate_with_metadata",
                new=AsyncMock(side_effect=upstream_error),
            ),
            patch.object(worker, "enqueue_generation_task", new=AsyncMock()) as enqueue,
        ):
            await worker.process_task(task_id)

        enqueue.assert_not_awaited()

        async with self.session_factory() as db:
            task = await db.get(GenerationTask, task_id)
            user = await db.get(User, user_id)

        self.assertEqual(task.status, GenerationTaskStatus.REFUNDED)
        self.assertIn("request_id=req_zilan_502", task.error_message)
        self.assertIn("size=3840x2160", task.error_message)
        self.assertEqual(task.upstream_endpoint, "/v1/images/generations")
        self.assertEqual(task.upstream_request_id, "req_zilan_502")
        self.assertEqual(task.upstream_request_size, "3840x2160")
        self.assertEqual(task.upstream_content_type, "application/json; charset=utf-8")
        self.assertEqual(task.upstream_elapsed_seconds, 68.2)
        self.assertEqual(task.upstream_header_seconds, 67.8)
        self.assertEqual(task.upstream_body_seconds, 0.0)
        self.assertEqual(task.upstream_body_bytes, 308)
        self.assertEqual(task.upstream_content_length, 308)
        self.assertEqual(user.monthly_quota_remaining, 3)


if __name__ == "__main__":
    unittest.main()
