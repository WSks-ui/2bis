from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models import ApiKeyConfig, User
from app.schemas import (
    AdminApiKeyCreate,
    AdminApiKeyResponse,
    AdminApiKeyTestRequest,
    AdminApiKeyTestResponse,
    AdminApiKeyUpdate,
)
from app.services.api_key_manager import (
    ApiKeyConfigError,
    decrypt_api_key,
    deactivate_other_configs,
    encrypt_api_key,
    invalidate_active_api_config_cache,
    mask_api_key,
    normalize_api_url,
    normalize_response_format,
    probe_api_key,
    write_admin_audit,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def api_key_response(config: ApiKeyConfig) -> AdminApiKeyResponse:
    return AdminApiKeyResponse(
        id=config.id,
        name=config.name,
        provider=config.provider,
        api_url=config.api_url,
        key_mask=config.key_mask,
        response_format=config.response_format,
        send_quality=config.send_quality,
        is_active=config.is_active,
        is_enabled=config.is_enabled,
        circuit_state=config.circuit_state,
        circuit_reason=config.circuit_reason,
        circuit_open_until=config.circuit_open_until,
        failure_count=config.failure_count,
        last_failure_at=config.last_failure_at,
        last_test_status=config.last_test_status,
        last_test_message=config.last_test_message,
        last_tested_at=config.last_tested_at,
        last_used_at=config.last_used_at,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


async def get_api_key_or_404(db: AsyncSession, config_id: int) -> ApiKeyConfig:
    config = await db.get(ApiKeyConfig, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="API Key config not found")
    return config


@router.get("/api-keys", response_model=list[AdminApiKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(ApiKeyConfig).order_by(ApiKeyConfig.is_active.desc(), ApiKeyConfig.updated_at.desc()))
    return [api_key_response(config) for config in result.scalars().all()]


@router.post("/api-keys", response_model=AdminApiKeyResponse)
async def create_api_key(
    data: AdminApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    try:
        api_url = normalize_api_url(data.api_url)
        response_format = normalize_response_format(data.response_format)
        encrypted = encrypt_api_key(data.api_key)
    except ApiKeyConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if data.test_before_activate:
        ok, message = await probe_api_key(api_url, data.api_key, response_format, data.send_quality)
        if not ok:
            raise HTTPException(status_code=400, detail=f"API Key test failed: {message}")

    now = datetime.utcnow()
    config = ApiKeyConfig(
        name=data.name.strip(),
        provider=data.provider.strip(),
        api_url=api_url,
        encrypted_api_key=encrypted,
        key_mask=mask_api_key(data.api_key),
        response_format=response_format,
        send_quality=data.send_quality,
        is_active=bool(data.activate and data.is_enabled),
        is_enabled=data.is_enabled,
        last_test_status="success" if data.test_before_activate else None,
        last_test_message="连接测试成功" if data.test_before_activate else None,
        last_tested_at=now if data.test_before_activate else None,
        created_by=current_admin.id,
        updated_by=current_admin.id,
        created_at=now,
        updated_at=now,
    )
    db.add(config)
    await db.flush()

    if config.is_active:
        await deactivate_other_configs(db, config.id)

    await write_admin_audit(
        db,
        current_admin.id,
        "api_key.create",
        "api_key_config",
        config.id,
        f"created {config.name} ({config.key_mask})",
    )
    await db.commit()
    await db.refresh(config)
    invalidate_active_api_config_cache()
    return api_key_response(config)


@router.patch("/api-keys/{config_id}", response_model=AdminApiKeyResponse)
async def update_api_key(
    config_id: int,
    data: AdminApiKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    config = await get_api_key_or_404(db, config_id)

    try:
        if data.name is not None:
            config.name = data.name.strip()
        if data.provider is not None:
            config.provider = data.provider.strip()
        if data.api_url is not None:
            config.api_url = normalize_api_url(data.api_url)
        if data.clear_response_format:
            config.response_format = None
        elif data.response_format is not None:
            config.response_format = normalize_response_format(data.response_format)
        if data.send_quality is not None:
            config.send_quality = data.send_quality
        if data.api_key is not None:
            config.encrypted_api_key = encrypt_api_key(data.api_key)
            config.key_mask = mask_api_key(data.api_key)
            config.last_test_status = None
            config.last_test_message = None
            config.last_tested_at = None
            config.failure_count = 0
            config.circuit_state = "closed"
            config.circuit_reason = None
            config.circuit_open_until = None
        if data.is_enabled is not None:
            config.is_enabled = data.is_enabled
            if not config.is_enabled:
                config.is_active = False
            else:
                config.circuit_state = "closed"
                config.circuit_reason = None
                config.circuit_open_until = None
                config.failure_count = 0
    except ApiKeyConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    config.updated_by = current_admin.id
    config.updated_at = datetime.utcnow()

    await write_admin_audit(
        db,
        current_admin.id,
        "api_key.update",
        "api_key_config",
        config.id,
        f"updated {config.name} ({config.key_mask})",
    )
    await db.commit()
    await db.refresh(config)
    invalidate_active_api_config_cache()
    return api_key_response(config)


@router.post("/api-keys/{config_id}/activate", response_model=AdminApiKeyResponse)
async def activate_api_key(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    config = await get_api_key_or_404(db, config_id)
    if not config.is_enabled:
        raise HTTPException(status_code=400, detail="Disabled API Key config cannot be activated")

    config.is_active = True
    config.circuit_state = "closed"
    config.circuit_reason = None
    config.circuit_open_until = None
    config.failure_count = 0
    config.updated_by = current_admin.id
    config.updated_at = datetime.utcnow()
    await deactivate_other_configs(db, config.id)
    await write_admin_audit(
        db,
        current_admin.id,
        "api_key.activate",
        "api_key_config",
        config.id,
        f"activated {config.name} ({config.key_mask})",
    )
    await db.commit()
    await db.refresh(config)
    invalidate_active_api_config_cache()
    return api_key_response(config)


@router.post("/api-keys/{config_id}/test", response_model=AdminApiKeyTestResponse)
async def test_api_key(
    config_id: int,
    data: AdminApiKeyTestRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    config = await get_api_key_or_404(db, config_id)
    test_data = data or AdminApiKeyTestRequest()

    try:
        api_url = normalize_api_url(test_data.api_url or config.api_url)
        api_key = test_data.api_key.strip() if test_data.api_key else decrypt_api_key(config.encrypted_api_key)
        response_format = normalize_response_format(
            test_data.response_format if test_data.response_format is not None else config.response_format
        )
    except ApiKeyConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ok, message = await probe_api_key(api_url, api_key, response_format, config.send_quality)
    now = datetime.utcnow()
    config.last_test_status = "success" if ok else "failed"
    config.last_test_message = message
    config.last_tested_at = now
    if ok:
        config.failure_count = 0
        config.circuit_state = "closed"
        config.circuit_reason = None
        config.circuit_open_until = None
    config.updated_by = current_admin.id
    config.updated_at = now

    await write_admin_audit(
        db,
        current_admin.id,
        "api_key.test",
        "api_key_config",
        config.id,
        f"tested {config.name}: {config.last_test_status}",
    )
    await db.commit()
    return AdminApiKeyTestResponse(ok=ok, message=message, tested_at=now)


@router.delete("/api-keys/{config_id}", status_code=204)
async def delete_api_key(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    config = await get_api_key_or_404(db, config_id)
    if config.is_active:
        raise HTTPException(status_code=400, detail="Active API Key config cannot be deleted")

    await write_admin_audit(
        db,
        current_admin.id,
        "api_key.delete",
        "api_key_config",
        config.id,
        f"deleted {config.name} ({config.key_mask})",
    )
    await db.delete(config)
    await db.commit()
    invalidate_active_api_config_cache()
