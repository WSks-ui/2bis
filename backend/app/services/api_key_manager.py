import base64
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import (
    AI_API_KEY,
    AI_API_URL,
    AI_IMAGE_RESPONSE_FORMAT,
    API_KEY_ALLOW_ENV_FALLBACK,
    API_KEY_CONFIG_CACHE_SECONDS,
    API_KEY_CIRCUIT_COOLDOWN_SECONDS,
    API_KEY_CIRCUIT_FAILURE_THRESHOLD,
    API_KEY_PROBE_TIMEOUT,
    API_KEY_ENCRYPTION_SECRET,
    SECRET_KEY,
)
from app.database import async_session
from app.models import AdminAuditLog, ApiKeyConfig


class ApiKeyConfigError(Exception):
    pass


@dataclass(frozen=True)
class ActiveApiConfig:
    api_url: str
    api_key: str
    response_format: str | None
    send_quality: bool = True
    config_id: int | None = None
    key_mask: str | None = None


class NoAvailableApiConfigError(Exception):
    pass


_fernet: Fernet | None = None
_cached_config: ActiveApiConfig | None = None
_cached_at = 0.0


def _fernet_key() -> bytes:
    secret = API_KEY_ENCRYPTION_SECRET or SECRET_KEY
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_fernet_key())
    return _fernet


def encrypt_api_key(api_key: str) -> str:
    cleaned = api_key.strip()
    if not cleaned:
        raise ApiKeyConfigError("API Key cannot be empty")
    return get_fernet().encrypt(cleaned.encode("utf-8")).decode("ascii")


def decrypt_api_key(encrypted_api_key: str) -> str:
    try:
        return get_fernet().decrypt(encrypted_api_key.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ApiKeyConfigError("API Key decrypt failed; check API_KEY_ENCRYPTION_SECRET") from exc


def mask_api_key(api_key: str) -> str:
    cleaned = api_key.strip()
    if len(cleaned) <= 8:
        return "*" * len(cleaned)
    prefix = cleaned[: min(6, len(cleaned) - 4)]
    suffix = cleaned[-4:]
    return f"{prefix}...{suffix}"


def normalize_response_format(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if normalized in {"", "auto", "none", "off", "disabled", "false"}:
        return None
    if normalized not in {"url", "b64_json"}:
        raise ApiKeyConfigError("response_format must be empty, url, or b64_json")
    return normalized


def normalize_api_url(api_url: str) -> str:
    cleaned = (api_url or "").strip().rstrip("/")
    if not cleaned:
        raise ApiKeyConfigError("API URL cannot be empty")
    if not cleaned.startswith(("http://", "https://")):
        raise ApiKeyConfigError("API URL must start with http:// or https://")
    return cleaned


def invalidate_active_api_config_cache() -> None:
    global _cached_config, _cached_at
    _cached_config = None
    _cached_at = 0.0


async def get_active_api_config(force_refresh: bool = False) -> ActiveApiConfig:
    global _cached_config, _cached_at
    now = time.monotonic()
    if (
        not force_refresh
        and _cached_config is not None
        and now - _cached_at <= API_KEY_CONFIG_CACHE_SECONDS
    ):
        return _cached_config

    async with async_session() as db:
        config, has_db_configs = await select_runtime_api_config(db)

    if config is not None:
        active = ActiveApiConfig(
            api_url=normalize_api_url(config.api_url),
            api_key=decrypt_api_key(config.encrypted_api_key),
            response_format=normalize_response_format(config.response_format),
            send_quality=bool(config.send_quality),
            config_id=config.id,
            key_mask=config.key_mask,
        )
    elif not has_db_configs or API_KEY_ALLOW_ENV_FALLBACK:
        # 只有管理员控制台尚未接管运行时 Key 时，回退到 .env 才安全。
        # 一旦数据库里存在通道，隐式回退会掩盖熔断状态，并把高成本生图请求发给非预期上游。
        active = ActiveApiConfig(
            api_url=normalize_api_url(AI_API_URL),
            api_key=AI_API_KEY,
            response_format=normalize_response_format(AI_IMAGE_RESPONSE_FORMAT),
            send_quality=True,
            config_id=None,
            key_mask=mask_api_key(AI_API_KEY) if AI_API_KEY else None,
        )
    else:
        raise NoAvailableApiConfigError("没有可用的数据库 API 通道，且已禁止回退到 .env API Key。")

    _cached_config = active
    _cached_at = now
    return active


def is_circuit_open(config: ApiKeyConfig, now: datetime | None = None) -> bool:
    if config.circuit_state != "open":
        return False
    if config.circuit_open_until is None:
        return True
    return config.circuit_open_until > (now or datetime.utcnow())


async def select_runtime_api_config(db: AsyncSession) -> tuple[ApiKeyConfig | None, bool]:
    now = datetime.utcnow()
    # 禁用的配置也要计入“已有数据库通道”；除非管理员显式允许，
    # 否则不应因为所有通道禁用而静默回退到 .env。
    has_db_configs = (
        await db.execute(select(ApiKeyConfig.id).limit(1))
    ).scalar_one_or_none() is not None
    result = await db.execute(
        select(ApiKeyConfig)
        .where(ApiKeyConfig.is_enabled.is_(True))
        .order_by(ApiKeyConfig.is_active.desc(), ApiKeyConfig.updated_at.desc(), ApiKeyConfig.id.desc())
    )
    configs = result.scalars().all()
    selected = next((config for config in configs if not is_circuit_open(config, now)), None)
    if selected is None:
        return None, has_db_configs

    if not selected.is_active:
        # 懒提升最新的健康启用通道，生成请求无需等待管理员手动激活即可恢复。
        await db.execute(
            update(ApiKeyConfig)
            .where(ApiKeyConfig.id != selected.id, ApiKeyConfig.is_active.is_(True))
            .values(is_active=False, updated_at=now)
        )
        selected.is_active = True
        selected.updated_at = now
        await db.commit()
        await db.refresh(selected)
        invalidate_active_api_config_cache()

    return selected, has_db_configs


async def touch_api_config_used(config_id: int | None) -> None:
    if config_id is None:
        return
    async with async_session() as db:
        await db.execute(
            update(ApiKeyConfig)
            .where(ApiKeyConfig.id == config_id)
            .values(
                last_used_at=datetime.utcnow(),
                failure_count=0,
                circuit_state="closed",
                circuit_reason=None,
                circuit_open_until=None,
            )
        )
        await db.commit()


async def mark_api_config_failed(
    config_id: int | None,
    message: str,
    *,
    terminal: bool = False,
    update_test_status: bool = False,
) -> None:
    if config_id is None:
        return
    now = datetime.utcnow()
    open_until = now + timedelta(seconds=API_KEY_CIRCUIT_COOLDOWN_SECONDS)
    async with async_session() as db:
        config = await db.get(ApiKeyConfig, config_id)
        if config is None:
            return

        failure_count = int(config.failure_count or 0) + 1
        should_open = terminal or failure_count >= API_KEY_CIRCUIT_FAILURE_THRESHOLD
        values = {
            "failure_count": failure_count,
            "last_failure_at": now,
            "updated_at": now,
        }
        if update_test_status:
            values.update(
                {
                    "last_test_status": "failed",
                    "last_test_message": message[:500],
                    "last_tested_at": now,
                }
            )
        if should_open:
            values.update(
                {
                    "circuit_state": "open",
                    "circuit_reason": message[:500],
                    "circuit_open_until": None if terminal else open_until,
                    "is_active": False,
                }
            )

        await db.execute(
            update(ApiKeyConfig)
            .where(ApiKeyConfig.id == config_id)
            .values(**values)
        )
        await db.commit()
    invalidate_active_api_config_cache()


async def close_api_config_circuit(config_id: int | None) -> None:
    if config_id is None:
        return
    async with async_session() as db:
        await db.execute(
            update(ApiKeyConfig)
            .where(ApiKeyConfig.id == config_id)
            .values(
                failure_count=0,
                circuit_state="closed",
                circuit_reason=None,
                circuit_open_until=None,
                updated_at=datetime.utcnow(),
            )
        )
        await db.commit()
    invalidate_active_api_config_cache()


async def write_admin_audit(
    db: AsyncSession,
    admin_user_id: int,
    action: str,
    target_type: str,
    target_id: int | None = None,
    summary: str | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=summary,
            created_at=datetime.utcnow(),
        )
    )


async def deactivate_other_configs(db: AsyncSession, active_id: int) -> None:
    await db.execute(
        update(ApiKeyConfig)
        .where(ApiKeyConfig.id != active_id, ApiKeyConfig.is_active.is_(True))
        .values(is_active=False, updated_at=datetime.utcnow())
    )


def summarize_error(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        message = exc.__class__.__name__
    return message[:500]


async def probe_api_key(
    api_url: str,
    api_key: str,
    response_format: str | None = None,
    send_quality: bool = True,
    timeout_seconds: float = API_KEY_PROBE_TIMEOUT,
) -> tuple[bool, str]:
    normalize_response_format(response_format)

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, proxy=None, trust_env=False) as client:
            # 用 /models 做无成本连通性测试；部分上游对任何 /images 请求都会计费。
            request = client.build_request(
                "GET",
                f"{normalize_api_url(api_url)}/models",
                headers={"Authorization": f"Bearer {api_key.strip()}"},
            )
            response = await client.send(request, stream=True)
            try:
                if 200 <= response.status_code < 300:
                    return True, "连接测试成功（/models 验证通过，未发起生图请求）"

                await response.aread()
                detail = response.text
                try:
                    data = response.json()
                    detail = data.get("error", {}).get("message", detail)
                except Exception:
                    pass
                if response.status_code in {404, 405}:
                    return False, (
                        "上游不支持无成本 /models 测试，未发起生图请求；"
                        "请使用正式低规格任务验证图片生成接口。"
                    )
                return False, f"HTTP {response.status_code}: {detail[:360]}"
            finally:
                await response.aclose()
    except Exception as exc:
        return False, summarize_error(exc)
