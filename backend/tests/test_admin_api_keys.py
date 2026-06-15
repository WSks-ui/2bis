import unittest
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.dependencies import get_current_admin_user
from app.models import AdminAuditLog, ApiKeyConfig, User
from app.routers.admin import activate_api_key, create_api_key, list_api_keys, update_api_key
from app.schemas import AdminApiKeyCreate, AdminApiKeyUpdate
from app.services.api_key_manager import (
    ActiveApiConfig,
    NoAvailableApiConfigError,
    decrypt_api_key,
    get_active_api_config,
    invalidate_active_api_config_cache,
    mark_api_config_failed,
    probe_api_key,
)


class NeverReadBodyStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        raise AssertionError("probe should not download a successful response body")


class AdminApiKeysTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        invalidate_active_api_config_cache()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        invalidate_active_api_config_cache()
        await self.engine.dispose()

    async def create_user(self, is_admin: bool = False) -> User:
        async with self.session_factory() as db:
            user = User(username=f"user-{is_admin}", hashed_password="x", is_admin=is_admin)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user

    async def test_admin_dependency_rejects_regular_user(self) -> None:
        user = await self.create_user(is_admin=False)
        with self.assertRaises(Exception) as ctx:
            await get_current_admin_user(user)
        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)

    async def test_create_api_key_masks_and_encrypts_secret(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            response = await create_api_key(
                AdminApiKeyCreate(
                    name="primary",
                    provider="aiartmirror",
                    api_url="https://www.aiartmirror.com/v1",
                    api_key="sk-test-secret-1234",
                    activate=True,
                ),
                db=db,
                current_admin=admin,
            )

        self.assertEqual(response.name, "primary")
        self.assertTrue(response.is_active)
        self.assertEqual(response.key_mask, "sk-tes...1234")
        self.assertTrue(response.send_quality)

        async with self.session_factory() as db:
            config = await db.get(ApiKeyConfig, response.id)
            audit = (await db.execute(select(AdminAuditLog))).scalar_one()

        self.assertNotIn("sk-test-secret-1234", config.encrypted_api_key)
        self.assertEqual(decrypt_api_key(config.encrypted_api_key), "sk-test-secret-1234")
        self.assertEqual(audit.action, "api_key.create")

    async def test_activating_one_key_deactivates_previous_active_key(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            first = await create_api_key(
                AdminApiKeyCreate(name="first", api_key="sk-first-1234", activate=True),
                db=db,
                current_admin=admin,
            )
            second = await create_api_key(
                AdminApiKeyCreate(name="second", api_key="sk-second-1234", activate=False),
                db=db,
                current_admin=admin,
            )

        async with self.session_factory() as db:
            await activate_api_key(second.id, db=db, current_admin=admin)

        async with self.session_factory() as db:
            first_config = await db.get(ApiKeyConfig, first.id)
            second_config = await db.get(ApiKeyConfig, second.id)

        self.assertFalse(first_config.is_active)
        self.assertTrue(second_config.is_active)

    async def test_update_can_clear_response_format_and_disable_active_key(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            created = await create_api_key(
                AdminApiKeyCreate(
                    name="primary",
                    api_key="sk-primary-1234",
                    response_format="url",
                    activate=True,
                ),
                db=db,
                current_admin=admin,
            )

        async with self.session_factory() as db:
            updated = await update_api_key(
                created.id,
                AdminApiKeyUpdate(clear_response_format=True, is_enabled=False),
                db=db,
                current_admin=admin,
            )

        self.assertIsNone(updated.response_format)
        self.assertFalse(updated.is_enabled)
        self.assertFalse(updated.is_active)

    async def test_create_can_test_before_activate(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            with patch("app.routers.admin.probe_api_key", new=AsyncMock(return_value=(True, "ok"))) as probe:
                response = await create_api_key(
                    AdminApiKeyCreate(
                        name="tested",
                        api_key="sk-tested-1234",
                        send_quality=False,
                        test_before_activate=True,
                    ),
                    db=db,
                    current_admin=admin,
                )

        probe.assert_awaited_once_with(
            "https://www.aiartmirror.com/v1",
            "sk-tested-1234",
            None,
            False,
        )
        self.assertEqual(response.last_test_status, "success")
        self.assertIsNotNone(response.last_tested_at)

    async def test_probe_uses_models_endpoint_without_reading_success_body(self) -> None:
        seen_request = {}

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal seen_request
            seen_request = {
                "method": request.method,
                "url": str(request.url),
                "body": request.read(),
            }
            return httpx.Response(
                200,
                stream=NeverReadBodyStream(),
                request=request,
                headers={"content-type": "application/json"},
            )

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient

        def client_factory(*args, **kwargs):
            kwargs["transport"] = transport
            return real_async_client(*args, **kwargs)

        with patch("app.services.api_key_manager.httpx.AsyncClient", side_effect=client_factory):
            ok, message = await probe_api_key(
                "https://api.zilan520.shop/v1",
                "sk-test-1234",
                send_quality=False,
            )

        self.assertTrue(ok)
        self.assertIn("/models", message)
        self.assertEqual(seen_request["method"], "GET")
        self.assertEqual(seen_request["url"], "https://api.zilan520.shop/v1/models")
        self.assertEqual(seen_request["body"], b"")

    async def test_probe_reads_error_body_for_non_200_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                502,
                json={"error": {"message": "upstream bad gateway"}},
                request=request,
            )

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient

        def client_factory(*args, **kwargs):
            kwargs["transport"] = transport
            return real_async_client(*args, **kwargs)

        with patch("app.services.api_key_manager.httpx.AsyncClient", side_effect=client_factory):
            ok, message = await probe_api_key(
                "https://api.zilan520.shop/v1",
                "sk-test-1234",
                send_quality=False,
            )

        self.assertFalse(ok)
        self.assertIn("HTTP 502", message)
        self.assertIn("upstream bad gateway", message)

    async def test_probe_reports_no_cost_test_when_models_endpoint_is_missing(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": {"message": "not found"}}, request=request)

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient

        def client_factory(*args, **kwargs):
            kwargs["transport"] = transport
            return real_async_client(*args, **kwargs)

        with patch("app.services.api_key_manager.httpx.AsyncClient", side_effect=client_factory):
            ok, message = await probe_api_key("https://api.example/v1", "sk-test-1234")

        self.assertFalse(ok)
        self.assertIn("未发起生图请求", message)

    async def test_update_can_toggle_quality_parameter(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            created = await create_api_key(
                AdminApiKeyCreate(name="zilan", api_key="sk-zilan-1234", send_quality=True),
                db=db,
                current_admin=admin,
            )

        async with self.session_factory() as db:
            updated = await update_api_key(
                created.id,
                AdminApiKeyUpdate(send_quality=False),
                db=db,
                current_admin=admin,
            )

        self.assertFalse(updated.send_quality)

        async with self.session_factory() as db:
            config = await db.get(ApiKeyConfig, created.id)

        self.assertFalse(config.send_quality)

    async def test_list_api_keys_never_returns_full_secret(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            await create_api_key(
                AdminApiKeyCreate(name="primary", api_key="sk-hidden-secret-1234"),
                db=db,
                current_admin=admin,
            )

        async with self.session_factory() as db:
            configs = await list_api_keys(db=db, current_admin=admin)

        dumped = str([config.model_dump() for config in configs])
        self.assertIn("sk-hid...1234", dumped)
        self.assertNotIn("sk-hidden-secret-1234", dumped)

    async def test_terminal_failure_opens_circuit_and_runtime_selects_backup(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            primary = await create_api_key(
                AdminApiKeyCreate(name="primary", api_key="sk-primary-1234", activate=True),
                db=db,
                current_admin=admin,
            )
            backup = await create_api_key(
                AdminApiKeyCreate(name="backup", api_key="sk-backup-1234", activate=False),
                db=db,
                current_admin=admin,
            )

        with patch("app.services.api_key_manager.async_session", self.session_factory):
            await mark_api_config_failed(primary.id, "no remaining credits", terminal=True)
            active = await get_active_api_config(force_refresh=True)

        self.assertEqual(active.config_id, backup.id)

        async with self.session_factory() as db:
            primary_config = await db.get(ApiKeyConfig, primary.id)
            backup_config = await db.get(ApiKeyConfig, backup.id)

        self.assertEqual(primary_config.circuit_state, "open")
        self.assertIsNone(primary_config.circuit_open_until)
        self.assertFalse(primary_config.is_active)
        self.assertTrue(backup_config.is_active)
        self.assertEqual(primary_config.failure_count, 1)

    async def test_runtime_never_selects_disabled_backup_after_active_key_fails(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            primary = await create_api_key(
                AdminApiKeyCreate(name="primary", api_key="sk-primary-1234", activate=True),
                db=db,
                current_admin=admin,
            )
            disabled_backup = await create_api_key(
                AdminApiKeyCreate(
                    name="disabled-backup",
                    api_key="sk-disabled-backup-1234",
                    activate=False,
                    is_enabled=False,
                ),
                db=db,
                current_admin=admin,
            )

        with (
            patch("app.services.api_key_manager.async_session", self.session_factory),
            patch("app.services.api_key_manager.API_KEY_ALLOW_ENV_FALLBACK", False),
        ):
            await mark_api_config_failed(primary.id, "daily usage limit exceeded", terminal=True)
            with self.assertRaises(NoAvailableApiConfigError):
                await get_active_api_config(force_refresh=True)

        async with self.session_factory() as db:
            disabled_config = await db.get(ApiKeyConfig, disabled_backup.id)

        self.assertFalse(disabled_config.is_enabled)
        self.assertFalse(disabled_config.is_active)

    async def test_runtime_revalidates_cached_config_before_use(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            cached = await create_api_key(
                AdminApiKeyCreate(name="cached", api_key="sk-cached-1234", activate=True),
                db=db,
                current_admin=admin,
            )
            backup = await create_api_key(
                AdminApiKeyCreate(name="backup", api_key="sk-backup-1234", activate=False),
                db=db,
                current_admin=admin,
            )
            cached_config = await db.get(ApiKeyConfig, cached.id)
            cached_config.is_enabled = False
            cached_config.is_active = False
            await db.commit()

        stale_active = ActiveApiConfig(
            api_url=cached.api_url,
            api_key="sk-cached-1234",
            response_format=None,
            config_id=cached.id,
            key_mask=cached.key_mask,
        )

        with (
            patch("app.services.api_key_manager.async_session", self.session_factory),
            patch("app.services.api_key_manager._cached_config", stale_active),
            patch("app.services.api_key_manager._cached_at", 10**12),
        ):
            active = await get_active_api_config()

        self.assertEqual(active.config_id, backup.id)

    async def test_runtime_does_not_fallback_to_env_when_db_configs_are_unavailable(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            primary = await create_api_key(
                AdminApiKeyCreate(name="primary", api_key="sk-primary-1234", activate=True),
                db=db,
                current_admin=admin,
            )

        with (
            patch("app.services.api_key_manager.async_session", self.session_factory),
            patch("app.services.api_key_manager.API_KEY_ALLOW_ENV_FALLBACK", False),
        ):
            await mark_api_config_failed(primary.id, "bad gateway", terminal=True)
            with self.assertRaises(NoAvailableApiConfigError):
                await get_active_api_config(force_refresh=True)

    async def test_runtime_does_not_fallback_to_env_when_db_configs_are_disabled(self) -> None:
        admin = await self.create_user(is_admin=True)
        async with self.session_factory() as db:
            await create_api_key(
                AdminApiKeyCreate(
                    name="disabled",
                    api_key="sk-disabled-1234",
                    activate=False,
                    is_enabled=False,
                ),
                db=db,
                current_admin=admin,
            )

        with (
            patch("app.services.api_key_manager.async_session", self.session_factory),
            patch("app.services.api_key_manager.API_KEY_ALLOW_ENV_FALLBACK", False),
        ):
            with self.assertRaises(NoAvailableApiConfigError):
                await get_active_api_config(force_refresh=True)


if __name__ == "__main__":
    unittest.main()
