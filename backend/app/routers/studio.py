import base64
import os
import json
import math
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import GENERATION_MAX_RETRIES, IMAGE_DIR, IMAGE_URL_PREFIX, MAX_UPLOAD_SIZE
from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    CanvasItem,
    CanvasRelation,
    GenerateHistory,
    GenerationTask,
    GenerationTaskStatus,
    User,
    Workspace,
    WorkspaceAsset,
)
from app.routers.generate import task_response
from app.schemas import (
    CanvasBulkUpdateRequest,
    CanvasBulkUpdateResponse,
    CanvasItemCreate,
    CanvasItemResponse,
    CanvasItemUpdate,
    CanvasRelationCreate,
    CanvasRelationResponse,
    CanvasRelationUpdate,
    CanvasResponse,
    HistoryImportRequest,
    StudioGenerateRequest,
    StudioGenerateResponse,
    StudioTaskStatusResponse,
    StudioAssetResponse,
    StudioAssetUpdate,
    StudioAssetUploadResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.generation_options import GenerationOptions, GenerationOptionsError
from app.services.image_derivatives import ensure_thumbnail
from app.services.image_storage import save_data_url
from app.services.quota_manager import QuotaError, QuotaManager
from app.services.studio_settlement import json_dumps as settlement_json_dumps
from app.services.studio_settlement import settle_studio_task_result
from app.services.task_queue import enqueue_generation_task
from app.services.upload_storage import save_upload_file

router = APIRouter(prefix="/workspaces", tags=["studio"])

ALLOWED_ITEM_TYPES = {"image", "prompt", "note", "task", "group", "frame"}
ALLOWED_RELATION_TYPES = {
    "style_reference",
    "character_reference",
    "composition_reference",
    "variant_of",
    "edit_source",
    "mask_for",
    "note_for",
    "same_series",
}
STUDIO_GENERATION_MODES = {"text2img", "ref2img", "edit"}
MAX_STUDIO_REFERENCE_IMAGES = 3
REMOTE_SOURCE_TIMEOUT = 20.0


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _json_dumps(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _workspace_response(workspace: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        cover_asset_id=workspace.cover_asset_id,
        canvas_revision=workspace.canvas_revision,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        last_opened_at=workspace.last_opened_at,
        archived_at=workspace.archived_at,
    )


def _asset_response(asset: WorkspaceAsset) -> StudioAssetResponse:
    return StudioAssetResponse(
        id=asset.id,
        workspace_id=asset.workspace_id,
        asset_type=asset.asset_type,
        source_type=asset.source_type,
        title=asset.title,
        url=asset.url,
        thumbnail_url=asset.thumbnail_url,
        mime_type=asset.mime_type,
        width=asset.width,
        height=asset.height,
        text_content=asset.text_content,
        task_id=asset.task_id,
        history_id=asset.history_id,
        parent_asset_id=asset.parent_asset_id,
        metadata=_json_loads(asset.metadata_json),
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _item_response(item: CanvasItem, asset: WorkspaceAsset | None = None) -> CanvasItemResponse:
    return CanvasItemResponse(
        id=item.id,
        workspace_id=item.workspace_id,
        asset_id=item.asset_id,
        task_id=item.task_id,
        item_type=item.item_type,
        x=item.x,
        y=item.y,
        width=item.width,
        height=item.height,
        rotation=item.rotation,
        z_index=item.z_index,
        locked=item.locked,
        title=item.title,
        data=_json_loads(item.data_json),
        asset=_asset_response(asset) if asset is not None else None,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _relation_response(relation: CanvasRelation) -> CanvasRelationResponse:
    return CanvasRelationResponse(
        id=relation.id,
        workspace_id=relation.workspace_id,
        source_item_id=relation.source_item_id,
        target_item_id=relation.target_item_id,
        relation_type=relation.relation_type,
        label=relation.label,
        strength=relation.strength,
        data=_json_loads(relation.data_json),
        created_at=relation.created_at,
        updated_at=relation.updated_at,
    )


async def _get_workspace(db: AsyncSession, workspace_id: int, user_id: int) -> Workspace:
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id,
            Workspace.deleted_at.is_(None),
        )
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


async def _get_asset(db: AsyncSession, workspace_id: int, asset_id: int, user_id: int) -> WorkspaceAsset:
    result = await db.execute(
        select(WorkspaceAsset).where(
            WorkspaceAsset.id == asset_id,
            WorkspaceAsset.workspace_id == workspace_id,
            WorkspaceAsset.user_id == user_id,
            WorkspaceAsset.deleted_at.is_(None),
        )
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


async def _get_item(db: AsyncSession, workspace_id: int, item_id: int, user_id: int) -> CanvasItem:
    result = await db.execute(
        select(CanvasItem).where(
            CanvasItem.id == item_id,
            CanvasItem.workspace_id == workspace_id,
            CanvasItem.user_id == user_id,
            CanvasItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Canvas item not found")
    return item


async def _get_item_optional(db: AsyncSession, workspace_id: int, item_id: int, user_id: int) -> CanvasItem | None:
    result = await db.execute(
        select(CanvasItem).where(
            CanvasItem.id == item_id,
            CanvasItem.workspace_id == workspace_id,
            CanvasItem.user_id == user_id,
            CanvasItem.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _get_task(db: AsyncSession, task_id: int, user_id: int) -> GenerationTask:
    result = await db.execute(
        select(GenerationTask).where(
            GenerationTask.id == task_id,
            GenerationTask.user_id == user_id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _get_relation(db: AsyncSession, workspace_id: int, relation_id: int, user_id: int) -> CanvasRelation:
    result = await db.execute(
        select(CanvasRelation).where(
            CanvasRelation.id == relation_id,
            CanvasRelation.workspace_id == workspace_id,
            CanvasRelation.user_id == user_id,
            CanvasRelation.deleted_at.is_(None),
        )
    )
    relation = result.scalar_one_or_none()
    if relation is None:
        raise HTTPException(status_code=404, detail="Relation not found")
    return relation


def _touch_canvas(workspace: Workspace) -> None:
    # revision 是画布自动保存的轻量并发控制。任何节点或连线变更都必须递增。
    workspace.canvas_revision += 1
    workspace.updated_at = datetime.utcnow()


async def _load_item_assets(db: AsyncSession, items: list[CanvasItem]) -> dict[int, WorkspaceAsset]:
    asset_ids = {item.asset_id for item in items if item.asset_id is not None}
    if not asset_ids:
        return {}
    result = await db.execute(
        select(WorkspaceAsset).where(
            WorkspaceAsset.id.in_(asset_ids),
            WorkspaceAsset.deleted_at.is_(None),
        )
    )
    return {asset.id: asset for asset in result.scalars().all()}


async def _create_canvas_item(
    db: AsyncSession,
    workspace: Workspace,
    current_user: User,
    payload: CanvasItemCreate,
) -> CanvasItem:
    if payload.item_type not in ALLOWED_ITEM_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported canvas item type")
    if payload.asset_id is not None:
        await _get_asset(db, workspace.id, payload.asset_id, current_user.id)
    if payload.task_id is not None:
        await _get_task(db, payload.task_id, current_user.id)

    item = CanvasItem(
        workspace_id=workspace.id,
        user_id=current_user.id,
        asset_id=payload.asset_id,
        task_id=payload.task_id,
        item_type=payload.item_type,
        x=payload.x,
        y=payload.y,
        width=payload.width,
        height=payload.height,
        rotation=payload.rotation,
        z_index=payload.z_index,
        locked=payload.locked,
        title=payload.title,
        data_json=_json_dumps(payload.data),
    )
    db.add(item)
    _touch_canvas(workspace)
    return item


def _apply_item_patch(item: CanvasItem, patch: CanvasItemUpdate) -> None:
    for field_name in ("x", "y", "width", "height", "rotation", "z_index", "locked", "title"):
        value = getattr(patch, field_name)
        if value is not None:
            setattr(item, field_name, value)
    if patch.data is not None:
        item.data_json = _json_dumps(patch.data)
    item.updated_at = datetime.utcnow()


def _image_dimensions(image_bytes: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            return image.width, image.height
    except Exception:
        return None, None


async def _create_image_asset_from_bytes(
    image_bytes: bytes,
    mime_type: str,
    filename: str | None,
    workspace: Workspace,
    current_user: User,
) -> WorkspaceAsset:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"
    image_url = await save_data_url(data_url, current_user.id)
    thumbnail_url = await ensure_thumbnail(image_url)
    width, height = _image_dimensions(image_bytes)
    return WorkspaceAsset(
        workspace_id=workspace.id,
        user_id=current_user.id,
        asset_type="image",
        source_type="upload",
        title=filename,
        url=image_url,
        thumbnail_url=thumbnail_url,
        mime_type=mime_type,
        width=width,
        height=height,
        metadata_json=_json_dumps({"original_filename": filename}),
    )


def _local_image_path_from_url(image_url: str | None) -> str | None:
    if not image_url or not image_url.startswith(f"{IMAGE_URL_PREFIX}/"):
        return None
    relative_path = image_url[len(f"{IMAGE_URL_PREFIX}/") :].replace("/", os.sep)
    image_root = Path(IMAGE_DIR).resolve()
    source_path = (image_root / relative_path).resolve()
    try:
        source_path.relative_to(image_root)
    except ValueError:
        return None
    return str(source_path)


async def _read_file_bytes(path: str) -> bytes:
    import asyncio

    def read_file() -> bytes:
        with open(path, "rb") as f:
            return f.read()

    return await asyncio.to_thread(read_file)


def _remote_filename_from_url(image_url: str | None, fallback: str) -> str:
    if not image_url:
        return fallback
    parsed = urlparse(image_url)
    name = Path(parsed.path).name
    return name or fallback


async def _download_remote_image_asset(asset: WorkspaceAsset) -> tuple[bytes, str, str]:
    if not asset.url or not asset.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Source image must be local or remote image URL")

    try:
        async with httpx.AsyncClient(timeout=REMOTE_SOURCE_TIMEOUT, follow_redirects=True, trust_env=False) as client:
            response = await client.get(asset.url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=400, detail=f"Remote source image returned HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail="Remote source image could not be downloaded") from exc

    image_bytes = response.content
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Remote source image is empty")
    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"Image too large (max {MAX_UPLOAD_SIZE // 1024 // 1024}MB)")

    raw_content_type = response.headers.get("content-type")
    remote_content_type = raw_content_type if str(raw_content_type or "").lower().startswith("image/") else None
    try:
        mime_type = GenerationOptions.validate_upload_image(image_bytes, remote_content_type or asset.mime_type)
    except GenerationOptionsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    fallback = f"asset-{asset.id}.{GenerationOptions.extension_for_mime(mime_type)}"
    filename = asset.title or _remote_filename_from_url(asset.url, fallback)
    return image_bytes, mime_type, filename


async def _read_local_image_asset(asset: WorkspaceAsset) -> tuple[bytes, str, str]:
    path = _local_image_path_from_url(asset.url)
    if path is None:
        return await _download_remote_image_asset(asset)
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Source image file is missing")

    image_bytes = await _read_file_bytes(path)
    try:
        mime_type = GenerationOptions.validate_upload_image(image_bytes, asset.mime_type)
    except GenerationOptionsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    filename = asset.title or f"asset-{asset.id}.{GenerationOptions.extension_for_mime(mime_type)}"
    return image_bytes, mime_type, filename


def _size_candidates() -> list[tuple[str, int, int]]:
    candidates: list[tuple[str, int, int]] = []
    for group in GenerationOptions.get_image_size_groups():
        for size in group.get("sizes", []):
            value = str(size.get("value") or "")
            try:
                width, height = GenerationOptions.parse_size(value)
            except GenerationOptionsError:
                continue
            candidates.append((value, width, height))
    return candidates


def _nearest_output_size(width: int | None, height: int | None) -> str:
    if not width or not height or width <= 0 or height <= 0:
        return "1024x1024"

    target_ratio = width / height
    target_area = width * height
    candidates = _size_candidates()
    if not candidates:
        return "1024x1024"

    def score(candidate: tuple[str, int, int]) -> tuple[float, int]:
        _, candidate_width, candidate_height = candidate
        candidate_ratio = candidate_width / candidate_height
        return (
            abs(math.log(candidate_ratio / target_ratio)),
            abs(candidate_width * candidate_height - target_area),
        )

    return min(candidates, key=score)[0]


def _validate_local_edit_mask(mask_bytes: bytes, content_type: str | None, expected_size: tuple[int, int]) -> None:
    if not mask_bytes:
        raise HTTPException(status_code=400, detail="Mask file cannot be empty")
    if len(mask_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"Mask too large (max {MAX_UPLOAD_SIZE // 1024 // 1024}MB)")
    claimed = (content_type or "").split(";", 1)[0].strip().lower()
    if claimed and claimed != "image/png":
        raise HTTPException(status_code=400, detail="Mask must be a PNG image")
    if not mask_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=400, detail="Mask must be a PNG image")

    try:
        with Image.open(BytesIO(mask_bytes)) as image:
            if image.format != "PNG":
                raise HTTPException(status_code=400, detail="Mask must be a PNG image")
            if image.size != expected_size:
                raise HTTPException(status_code=400, detail="Mask size must match source image")
            alpha = image.convert("RGBA").getchannel("A")
            alpha_min, _ = alpha.getextrema()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid mask image") from exc

    # 前端约定：用户涂抹区域 alpha=0，未涂抹区域 alpha=255。
    # 如果整张图 alpha 都是 255，说明用户没有标记任何要修改的区域，直接拒绝以免误扣费。
    if alpha_min >= 255:
        raise HTTPException(status_code=400, detail="Mask has no editable area")


async def _source_items_for_generation(
    db: AsyncSession,
    workspace: Workspace,
    source_item_ids: list[int],
    current_user: User,
) -> list[CanvasItem]:
    if not source_item_ids:
        return []
    unique_ids: list[int] = []
    seen: set[int] = set()
    for item_id in source_item_ids:
        if item_id not in seen:
            unique_ids.append(item_id)
            seen.add(item_id)

    items: list[CanvasItem] = []
    for item_id in unique_ids:
        items.append(await _get_item(db, workspace.id, item_id, current_user.id))
    return items


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Workspace)
        .where(
            Workspace.user_id == current_user.id,
            Workspace.deleted_at.is_(None),
        )
        .order_by(Workspace.updated_at.desc())
    )
    return [_workspace_response(workspace) for workspace in result.scalars().all()]


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = Workspace(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description,
        settings_json="{}",
        last_opened_at=datetime.utcnow(),
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return _workspace_response(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    workspace.last_opened_at = datetime.utcnow()
    await db.commit()
    await db.refresh(workspace)
    return _workspace_response(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    if payload.name is not None:
        workspace.name = payload.name.strip()
    if payload.description is not None:
        workspace.description = payload.description
    if payload.cover_asset_id is not None:
        await _get_asset(db, workspace.id, payload.cover_asset_id, current_user.id)
        workspace.cover_asset_id = payload.cover_asset_id
    workspace.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(workspace)
    return _workspace_response(workspace)


@router.delete("/{workspace_id}", status_code=204)
async def archive_workspace(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    now = datetime.utcnow()
    workspace.archived_at = now
    workspace.deleted_at = now
    workspace.updated_at = now
    await db.commit()


@router.get("/{workspace_id}/canvas", response_model=CanvasResponse)
async def get_canvas(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    workspace.last_opened_at = datetime.utcnow()

    items_result = await db.execute(
        select(CanvasItem)
        .where(
            CanvasItem.workspace_id == workspace.id,
            CanvasItem.user_id == current_user.id,
            CanvasItem.deleted_at.is_(None),
        )
        .order_by(CanvasItem.z_index.asc(), CanvasItem.id.asc())
    )
    items = items_result.scalars().all()
    item_assets = await _load_item_assets(db, items)

    relations_result = await db.execute(
        select(CanvasRelation)
        .where(
            CanvasRelation.workspace_id == workspace.id,
            CanvasRelation.user_id == current_user.id,
            CanvasRelation.deleted_at.is_(None),
        )
        .order_by(CanvasRelation.id.asc())
    )
    relations = relations_result.scalars().all()

    assets_result = await db.execute(
        select(WorkspaceAsset)
        .where(
            WorkspaceAsset.workspace_id == workspace.id,
            WorkspaceAsset.user_id == current_user.id,
            WorkspaceAsset.deleted_at.is_(None),
        )
        .order_by(WorkspaceAsset.created_at.desc())
    )
    assets = assets_result.scalars().all()
    await db.commit()
    await db.refresh(workspace)

    return CanvasResponse(
        workspace=_workspace_response(workspace),
        revision=workspace.canvas_revision,
        items=[_item_response(item, item_assets.get(item.asset_id)) for item in items],
        relations=[_relation_response(relation) for relation in relations],
        assets=[_asset_response(asset) for asset in assets],
    )


@router.post("/{workspace_id}/generate", response_model=StudioGenerateResponse)
async def generate_from_studio(
    workspace_id: int,
    payload: StudioGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    mode = (payload.mode or "text2img").strip().lower()
    if mode not in STUDIO_GENERATION_MODES:
        raise HTTPException(status_code=400, detail="Unsupported image generation mode")

    workspace = await _get_workspace(db, workspace_id, current_user.id)
    source_items = await _source_items_for_generation(db, workspace, payload.source_item_ids, current_user)
    image_source_items = [item for item in source_items if item.item_type == "image"]

    if mode == "ref2img" and not image_source_items:
        raise HTTPException(status_code=400, detail="Reference generation requires at least one image source")
    if mode == "ref2img" and len(image_source_items) > MAX_STUDIO_REFERENCE_IMAGES:
        raise HTTPException(status_code=400, detail=f"Reference generation supports up to {MAX_STUDIO_REFERENCE_IMAGES} images")
    if mode == "edit" and len(image_source_items) != 1:
        raise HTTPException(status_code=400, detail="Image edit requires exactly one image source")

    source_image_paths: list[str] = []
    source_image_mime_types: list[str] = []
    if mode in {"ref2img", "edit"}:
        for item in image_source_items:
            if item.asset_id is None:
                raise HTTPException(status_code=400, detail="Image source has no asset")
            asset = await _get_asset(db, workspace.id, item.asset_id, current_user.id)
            image_bytes, mime_type, filename = await _read_local_image_asset(asset)
            source_image_paths.append(await save_upload_file(image_bytes, current_user.id, filename))
            source_image_mime_types.append(mime_type)

    try:
        quality = GenerationOptions.normalize_quality(payload.quality)
        size = GenerationOptions.normalize_size(payload.size)
        workflow_type = QuotaManager.normalize_workflow_type(payload.workflow_type)
        workflow_preset = QuotaManager.normalize_workflow_preset(payload.workflow_preset)
        deduction = await QuotaManager.deduct_for_generation(db, current_user.id, quality, workflow_type)
    except (GenerationOptionsError, QuotaError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task = GenerationTask(
        user_id=current_user.id,
        workspace_id=workspace.id,
        mode=mode,
        prompt=prompt,
        quality=quality,
        size=size,
        points_cost=deduction.cost,
        balance_source=deduction.balance_source,
        workflow_type=deduction.workflow_type,
        workflow_cost=deduction.workflow_cost,
        workflow_preset=workflow_preset,
        source_image_path=source_image_paths[0] if source_image_paths else None,
        source_image_mime_type=source_image_mime_types[0] if source_image_mime_types else None,
        source_image_paths=json.dumps(source_image_paths, ensure_ascii=False) if source_image_paths else None,
        source_image_mime_types=json.dumps(source_image_mime_types, ensure_ascii=False) if source_image_mime_types else None,
        studio_source_item_ids_json=json.dumps([item.id for item in source_items], ensure_ascii=False),
        max_retries=GENERATION_MAX_RETRIES,
    )
    db.add(task)
    await db.flush()

    task_item = await _create_canvas_item(
        db,
        workspace,
        current_user,
        CanvasItemCreate(
            task_id=task.id,
            item_type="task",
            title=f"生成任务 #{task.id}",
            x=payload.x,
            y=payload.y,
            width=280,
            height=156,
            data={
                "status": task.status.value,
                "mode": mode,
                "prompt": prompt,
                "quality": quality,
                "size": size,
                "source_item_ids": [item.id for item in source_items],
            },
        ),
    )
    await db.flush()
    task.canvas_item_id = task_item.id
    await db.commit()
    await db.refresh(task)
    await db.refresh(task_item)

    try:
        await enqueue_generation_task(task.id)
    except Exception as e:
        await QuotaManager.refund_generation(db, current_user.id, task.points_cost, task.balance_source)
        task.status = GenerationTaskStatus.REFUNDED
        task.error_message = f"Task queue unavailable: {e}"
        task_item.data_json = _json_dumps(
            {
                **_json_loads(task_item.data_json),
                "status": task.status.value,
                "error_message": task.error_message,
            }
        )
        _touch_canvas(workspace)
        await db.commit()
        raise HTTPException(status_code=503, detail="任务队列暂不可用，请稍后重试")

    return StudioGenerateResponse(
        task=task_response(task),
        item=_item_response(task_item),
        revision=workspace.canvas_revision,
    )


@router.post("/{workspace_id}/local-edit", response_model=StudioGenerateResponse)
async def create_local_edit_task(
    workspace_id: int,
    source_item_id: int = Form(...),
    prompt: str = Form(...),
    quality: str = Form(default="low"),
    mask: UploadFile = File(...),
    x: float = Form(default=0),
    y: float = Form(default=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    workspace = await _get_workspace(db, workspace_id, current_user.id)
    source_item = await _get_item(db, workspace.id, source_item_id, current_user.id)
    if source_item.item_type != "image" or source_item.asset_id is None:
        raise HTTPException(status_code=400, detail="Local edit source must be an image node")

    asset = await _get_asset(db, workspace.id, source_item.asset_id, current_user.id)
    if asset.asset_type != "image" or not asset.url:
        raise HTTPException(status_code=400, detail="Local edit source asset is not an image")

    image_bytes, mime_type, filename = await _read_local_image_asset(asset)
    source_width, source_height = _image_dimensions(image_bytes)
    if not source_width or not source_height:
        raise HTTPException(status_code=400, detail="Source image dimensions cannot be read")

    mask_bytes = await mask.read()
    _validate_local_edit_mask(mask_bytes, mask.content_type, (source_width, source_height))

    try:
        normalized_quality = GenerationOptions.normalize_quality(quality)
        size = _nearest_output_size(source_width, source_height)
        deduction = await QuotaManager.deduct_for_generation(db, current_user.id, normalized_quality, "standard")
    except (GenerationOptionsError, QuotaError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    source_image_path = await save_upload_file(image_bytes, current_user.id, filename)
    source_mask_path = await save_upload_file(mask_bytes, current_user.id, f"mask-{source_item.id}.png")
    task = GenerationTask(
        user_id=current_user.id,
        workspace_id=workspace.id,
        mode="edit",
        prompt=normalized_prompt,
        quality=normalized_quality,
        size=size,
        points_cost=deduction.cost,
        balance_source=deduction.balance_source,
        workflow_type=deduction.workflow_type,
        workflow_cost=deduction.workflow_cost,
        source_image_path=source_image_path,
        source_image_mime_type=mime_type,
        source_image_paths=json.dumps([source_image_path], ensure_ascii=False),
        source_image_mime_types=json.dumps([mime_type], ensure_ascii=False),
        source_mask_path=source_mask_path,
        source_mask_mime_type="image/png",
        studio_source_item_ids_json=json.dumps([source_item.id], ensure_ascii=False),
        max_retries=GENERATION_MAX_RETRIES,
    )
    db.add(task)
    await db.flush()

    task_item = await _create_canvas_item(
        db,
        workspace,
        current_user,
        CanvasItemCreate(
            task_id=task.id,
            item_type="task",
            title=f"局部修改任务 #{task.id}",
            x=x,
            y=y,
            width=280,
            height=156,
            data={
                "status": task.status.value,
                "mode": "edit",
                "tool": "local_edit",
                "prompt": normalized_prompt,
                "quality": normalized_quality,
                "size": size,
                "source_item_ids": [source_item.id],
                "source_mask_mime_type": "image/png",
            },
        ),
    )
    await db.flush()
    task.canvas_item_id = task_item.id
    await db.commit()
    await db.refresh(task)
    await db.refresh(task_item)

    try:
        await enqueue_generation_task(task.id)
    except Exception as e:
        await QuotaManager.refund_generation(db, current_user.id, task.points_cost, task.balance_source)
        task.status = GenerationTaskStatus.REFUNDED
        task.error_message = f"Task queue unavailable: {e}"
        task_item.data_json = _json_dumps(
            {
                **_json_loads(task_item.data_json),
                "status": task.status.value,
                "error_message": task.error_message,
            }
        )
        _touch_canvas(workspace)
        await db.commit()
        raise HTTPException(status_code=503, detail="任务队列暂不可用，请稍后重试")

    return StudioGenerateResponse(
        task=task_response(task),
        item=_item_response(task_item),
        revision=workspace.canvas_revision,
    )


@router.get("/{workspace_id}/tasks/{task_id}", response_model=StudioTaskStatusResponse)
async def get_studio_task_status(
    workspace_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    result = await db.execute(
        select(GenerationTask).where(
            GenerationTask.id == task_id,
            GenerationTask.user_id == current_user.id,
            GenerationTask.workspace_id == workspace.id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    settled = await settle_studio_task_result(db, task)
    if settled.get("changed"):
        await db.commit()
        await db.refresh(workspace)

    task_item = settled.get("task_item")
    result_item = settled.get("result_item")
    asset = settled.get("asset")
    relations = settled.get("relations") or []

    if task_item is None and task.canvas_item_id is not None:
        task_item = await _get_item_optional(db, workspace.id, task.canvas_item_id, current_user.id)
    if asset is None:
        asset_result = await db.execute(
            select(WorkspaceAsset).where(
                WorkspaceAsset.workspace_id == workspace.id,
                WorkspaceAsset.user_id == current_user.id,
                WorkspaceAsset.task_id == task.id,
                WorkspaceAsset.source_type == "studio_generation",
                WorkspaceAsset.deleted_at.is_(None),
            )
        )
        asset = asset_result.scalar_one_or_none()
    if result_item is None and asset is not None:
        result_item_result = await db.execute(
            select(CanvasItem).where(
                CanvasItem.workspace_id == workspace.id,
                CanvasItem.user_id == current_user.id,
                CanvasItem.asset_id == asset.id,
                CanvasItem.task_id == task.id,
                CanvasItem.item_type == "image",
                CanvasItem.deleted_at.is_(None),
            )
        )
        result_item = result_item_result.scalar_one_or_none()

    return StudioTaskStatusResponse(
        task=task_response(task),
        task_item=_item_response(task_item) if task_item is not None else None,
        asset=_asset_response(asset) if asset is not None else None,
        result_item=_item_response(result_item, asset) if result_item is not None else None,
        relations=[_relation_response(relation) for relation in relations],
        revision=workspace.canvas_revision,
    )


@router.post("/{workspace_id}/canvas/items", response_model=CanvasItemResponse)
async def create_canvas_item(
    workspace_id: int,
    payload: CanvasItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    item = await _create_canvas_item(db, workspace, current_user, payload)
    await db.commit()
    await db.refresh(item)
    asset = await _get_asset(db, workspace.id, item.asset_id, current_user.id) if item.asset_id else None
    return _item_response(item, asset)


@router.patch("/{workspace_id}/canvas/items/{item_id}", response_model=CanvasItemResponse)
async def update_canvas_item(
    workspace_id: int,
    item_id: int,
    payload: CanvasItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    item = await _get_item(db, workspace.id, item_id, current_user.id)
    _apply_item_patch(item, payload)
    _touch_canvas(workspace)
    await db.commit()
    await db.refresh(item)
    asset = await _get_asset(db, workspace.id, item.asset_id, current_user.id) if item.asset_id else None
    return _item_response(item, asset)


@router.post("/{workspace_id}/canvas/items/bulk", response_model=CanvasBulkUpdateResponse)
async def bulk_update_canvas_items(
    workspace_id: int,
    payload: CanvasBulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    if payload.client_revision != workspace.canvas_revision:
        raise HTTPException(status_code=409, detail="Canvas revision conflict")

    updated_items: list[CanvasItem] = []
    for item_patch in payload.items:
        item = await _get_item(db, workspace.id, item_patch.id, current_user.id)
        _apply_item_patch(item, item_patch)
        updated_items.append(item)

    if updated_items:
        _touch_canvas(workspace)
    await db.commit()
    for item in updated_items:
        await db.refresh(item)

    assets = await _load_item_assets(db, updated_items)
    return CanvasBulkUpdateResponse(
        revision=workspace.canvas_revision,
        items=[_item_response(item, assets.get(item.asset_id)) for item in updated_items],
    )


@router.delete("/{workspace_id}/canvas/items/{item_id}", status_code=204)
async def delete_canvas_item(
    workspace_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    item = await _get_item(db, workspace.id, item_id, current_user.id)
    now = datetime.utcnow()
    item.deleted_at = now
    item.updated_at = now

    # 节点软删除后，相关连线也软删除，避免画布恢复时出现悬空关系。
    result = await db.execute(
        select(CanvasRelation).where(
            CanvasRelation.workspace_id == workspace.id,
            CanvasRelation.user_id == current_user.id,
            CanvasRelation.deleted_at.is_(None),
            or_(CanvasRelation.source_item_id == item.id, CanvasRelation.target_item_id == item.id),
        )
    )
    for relation in result.scalars().all():
        relation.deleted_at = now
        relation.updated_at = now
    _touch_canvas(workspace)
    await db.commit()


@router.post("/{workspace_id}/canvas/relations", response_model=CanvasRelationResponse)
async def create_canvas_relation(
    workspace_id: int,
    payload: CanvasRelationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    if payload.relation_type not in ALLOWED_RELATION_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported relation type")
    if payload.source_item_id == payload.target_item_id:
        raise HTTPException(status_code=400, detail="Relation source and target cannot be the same")
    await _get_item(db, workspace.id, payload.source_item_id, current_user.id)
    await _get_item(db, workspace.id, payload.target_item_id, current_user.id)

    relation = CanvasRelation(
        workspace_id=workspace.id,
        user_id=current_user.id,
        source_item_id=payload.source_item_id,
        target_item_id=payload.target_item_id,
        relation_type=payload.relation_type,
        label=payload.label,
        strength=payload.strength,
        data_json=_json_dumps(payload.data),
    )
    db.add(relation)
    _touch_canvas(workspace)
    await db.commit()
    await db.refresh(relation)
    return _relation_response(relation)


@router.patch("/{workspace_id}/canvas/relations/{relation_id}", response_model=CanvasRelationResponse)
async def update_canvas_relation(
    workspace_id: int,
    relation_id: int,
    payload: CanvasRelationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    relation = await _get_relation(db, workspace.id, relation_id, current_user.id)
    if payload.relation_type is not None:
        if payload.relation_type not in ALLOWED_RELATION_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported relation type")
        relation.relation_type = payload.relation_type
    if payload.label is not None:
        relation.label = payload.label
    if payload.strength is not None:
        relation.strength = payload.strength
    if payload.data is not None:
        relation.data_json = _json_dumps(payload.data)
    relation.updated_at = datetime.utcnow()
    _touch_canvas(workspace)
    await db.commit()
    await db.refresh(relation)
    return _relation_response(relation)


@router.delete("/{workspace_id}/canvas/relations/{relation_id}", status_code=204)
async def delete_canvas_relation(
    workspace_id: int,
    relation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    relation = await _get_relation(db, workspace.id, relation_id, current_user.id)
    relation.deleted_at = datetime.utcnow()
    relation.updated_at = datetime.utcnow()
    _touch_canvas(workspace)
    await db.commit()


@router.get("/{workspace_id}/assets", response_model=list[StudioAssetResponse])
async def list_assets(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    result = await db.execute(
        select(WorkspaceAsset)
        .where(
            WorkspaceAsset.workspace_id == workspace.id,
            WorkspaceAsset.user_id == current_user.id,
            WorkspaceAsset.deleted_at.is_(None),
        )
        .order_by(WorkspaceAsset.created_at.desc())
    )
    return [_asset_response(asset) for asset in result.scalars().all()]


@router.post("/{workspace_id}/assets/upload", response_model=StudioAssetUploadResponse)
async def upload_asset(
    workspace_id: int,
    image: UploadFile = File(...),
    title: str | None = Form(default=None),
    x: float = Form(default=0),
    y: float = Form(default=0),
    create_item: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image file cannot be empty")
    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"Image too large (max {MAX_UPLOAD_SIZE // 1024 // 1024}MB)")
    try:
        mime_type = GenerationOptions.validate_upload_image(image_bytes, image.content_type)
    except GenerationOptionsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    asset = await _create_image_asset_from_bytes(
        image_bytes=image_bytes,
        mime_type=mime_type,
        filename=title or image.filename,
        workspace=workspace,
        current_user=current_user,
    )
    db.add(asset)
    await db.flush()

    item = None
    if create_item:
        item = await _create_canvas_item(
            db,
            workspace,
            current_user,
            CanvasItemCreate(
                asset_id=asset.id,
                item_type="image",
                x=x,
                y=y,
                width=260,
                height=200,
                title=asset.title,
                data={"assetType": "image"},
            ),
        )
    await db.commit()
    await db.refresh(asset)
    if item is not None:
        await db.refresh(item)
    return StudioAssetUploadResponse(
        asset=_asset_response(asset),
        item=_item_response(item, asset) if item is not None else None,
    )


@router.post("/{workspace_id}/assets/import-history", response_model=StudioAssetUploadResponse)
async def import_history_asset(
    workspace_id: int,
    payload: HistoryImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    history_result = await db.execute(
        select(GenerateHistory).where(
            GenerateHistory.id == payload.history_id,
            GenerateHistory.user_id == current_user.id,
        )
    )
    history = history_result.scalar_one_or_none()
    if history is None:
        raise HTTPException(status_code=404, detail="History not found")
    if not history.image_url:
        raise HTTPException(status_code=400, detail="History has no image")

    existing_result = await db.execute(
        select(WorkspaceAsset).where(
            WorkspaceAsset.workspace_id == workspace.id,
            WorkspaceAsset.user_id == current_user.id,
            WorkspaceAsset.history_id == history.id,
            WorkspaceAsset.deleted_at.is_(None),
        )
    )
    asset = existing_result.scalar_one_or_none()
    if asset is None:
        asset = WorkspaceAsset(
            workspace_id=workspace.id,
            user_id=current_user.id,
            asset_type="image",
            source_type="history_import",
            title=f"历史记录 #{history.id}",
            url=history.image_url,
            thumbnail_url=await ensure_thumbnail(history.image_url),
            task_id=history.task_id,
            history_id=history.id,
            metadata_json=_json_dumps(
                {
                    "prompt": history.prompt,
                    "quality": history.quality,
                    "workflow_type": history.workflow_type,
                    "points_cost": history.points_cost,
                }
            ),
        )
        db.add(asset)
        await db.flush()

    item = None
    if payload.create_item:
        item = await _create_canvas_item(
            db,
            workspace,
            current_user,
            CanvasItemCreate(
                asset_id=asset.id,
                item_type="image",
                x=payload.x,
                y=payload.y,
                width=260,
                height=200,
                title=asset.title,
                data={"source": "history", "prompt": history.prompt},
            ),
        )
    await db.commit()
    await db.refresh(asset)
    if item is not None:
        await db.refresh(item)
    return StudioAssetUploadResponse(
        asset=_asset_response(asset),
        item=_item_response(item, asset) if item is not None else None,
    )


@router.patch("/{workspace_id}/assets/{asset_id}", response_model=StudioAssetResponse)
async def update_asset(
    workspace_id: int,
    asset_id: int,
    payload: StudioAssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_workspace(db, workspace_id, current_user.id)
    asset = await _get_asset(db, workspace_id, asset_id, current_user.id)
    if payload.title is not None:
        asset.title = payload.title
    if payload.metadata is not None:
        asset.metadata_json = _json_dumps(payload.metadata)
    asset.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(asset)
    return _asset_response(asset)


@router.delete("/{workspace_id}/assets/{asset_id}", status_code=204)
async def delete_asset(
    workspace_id: int,
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await _get_workspace(db, workspace_id, current_user.id)
    asset = await _get_asset(db, workspace.id, asset_id, current_user.id)
    now = datetime.utcnow()
    asset.deleted_at = now
    asset.updated_at = now

    # 素材删除采用软删除；仍在画布上的引用也一起软删除，文件清理由后续后台任务处理。
    items_result = await db.execute(
        select(CanvasItem).where(
            CanvasItem.workspace_id == workspace.id,
            CanvasItem.user_id == current_user.id,
            CanvasItem.asset_id == asset.id,
            CanvasItem.deleted_at.is_(None),
        )
    )
    for item in items_result.scalars().all():
        item.deleted_at = now
        item.updated_at = now
        relations_result = await db.execute(
            select(CanvasRelation).where(
                CanvasRelation.workspace_id == workspace.id,
                CanvasRelation.user_id == current_user.id,
                CanvasRelation.deleted_at.is_(None),
                or_(CanvasRelation.source_item_id == item.id, CanvasRelation.target_item_id == item.id),
            )
        )
        for relation in relations_result.scalars().all():
            relation.deleted_at = now
            relation.updated_at = now
    _touch_canvas(workspace)
    await db.commit()
