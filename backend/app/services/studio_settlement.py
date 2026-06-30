import json
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CanvasItem, CanvasRelation, GenerationTask, GenerationTaskStatus, Workspace, WorkspaceAsset
from app.services.image_derivatives import ensure_thumbnail


def json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def json_dumps(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def json_list(value: str | None) -> list[int]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    result: list[int] = []
    for item in loaded:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


def touch_canvas(workspace: Workspace) -> None:
    workspace.canvas_revision += 1
    workspace.updated_at = datetime.utcnow()


async def _load_active_item(db: AsyncSession, item_id: int | None, workspace_id: int, user_id: int) -> CanvasItem | None:
    if item_id is None:
        return None
    result = await db.execute(
        select(CanvasItem).where(
            CanvasItem.id == item_id,
            CanvasItem.workspace_id == workspace_id,
            CanvasItem.user_id == user_id,
            CanvasItem.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _load_source_items(db: AsyncSession, task: GenerationTask) -> list[CanvasItem]:
    source_ids = json_list(task.studio_source_item_ids_json)
    if not source_ids or task.workspace_id is None:
        return []
    result = await db.execute(
        select(CanvasItem)
        .where(
            CanvasItem.id.in_(source_ids),
            CanvasItem.workspace_id == task.workspace_id,
            CanvasItem.user_id == task.user_id,
            CanvasItem.deleted_at.is_(None),
        )
        .order_by(CanvasItem.id.asc())
    )
    by_id = {item.id: item for item in result.scalars().all()}
    return [by_id[item_id] for item_id in source_ids if item_id in by_id]


def _relation_type_for_source(task: GenerationTask, source_item: CanvasItem) -> str:
    if source_item.item_type in {"prompt", "note"}:
        return "note_for"
    if task.mode == "edit":
        return "edit_source"
    if task.mode == "ref2img":
        return "style_reference"
    return "variant_of"


def _relation_label(relation_type: str) -> str:
    labels = {
        "style_reference": "风格参考",
        "character_reference": "角色参考",
        "composition_reference": "构图参考",
        "variant_of": "变体来源",
        "edit_source": "编辑来源",
        "note_for": "说明",
        "same_series": "同系列",
    }
    return labels.get(relation_type, relation_type)


async def settle_studio_task_result(db: AsyncSession, task: GenerationTask) -> dict[str, Any]:
    """把 Studio 任务的成功结果幂等落到素材库和画布。

    worker 会主动调用这里；前端轮询任务状态时也会调用一次，避免 worker 成功后因为旧版本代码或中途异常
    没有完成回填，导致用户只看到历史记录而画布没有结果节点。
    """
    if task.workspace_id is None:
        return {"asset": None, "result_item": None, "task_item": None, "relations": [], "changed": False}

    workspace = await db.get(Workspace, task.workspace_id)
    if workspace is None or workspace.deleted_at is not None or workspace.user_id != task.user_id:
        return {"asset": None, "result_item": None, "task_item": None, "relations": [], "changed": False}

    task_item = await _load_active_item(db, task.canvas_item_id, workspace.id, task.user_id)
    changed = False
    source_items = await _load_source_items(db, task)

    if task_item is not None:
        data = json_loads(task_item.data_json)
        next_data = {
            **data,
            "status": task.status.value,
            "progress_stage": task.progress_stage,
            "progress_message": task.progress_message,
            "error_message": task.error_message,
            "image_url": task.image_url,
        }
        if next_data != data:
            task_item.data_json = json_dumps(next_data)
            task_item.updated_at = datetime.utcnow()
            changed = True

    if task.status != GenerationTaskStatus.SUCCESS or not task.image_url:
        if changed:
            touch_canvas(workspace)
        return {"asset": None, "result_item": None, "task_item": task_item, "relations": [], "changed": changed}

    result = await db.execute(
        select(WorkspaceAsset).where(
            WorkspaceAsset.workspace_id == workspace.id,
            WorkspaceAsset.user_id == task.user_id,
            WorkspaceAsset.task_id == task.id,
            WorkspaceAsset.source_type == "studio_generation",
            WorkspaceAsset.deleted_at.is_(None),
        )
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = WorkspaceAsset(
            workspace_id=workspace.id,
            user_id=task.user_id,
            asset_type="image",
            source_type="studio_generation",
            title=f"生成结果 #{task.id}",
            url=task.image_url,
            thumbnail_url=await ensure_thumbnail(task.image_url),
            task_id=task.id,
            metadata_json=json_dumps(
                {
                    "prompt": task.prompt,
                    "mode": task.mode,
                    "quality": task.quality,
                    "size": task.size,
                    "workflow_type": task.workflow_type,
                    "workflow_preset": task.workflow_preset,
                    "source_item_ids": [item.id for item in source_items],
                    "has_mask": bool(task.source_mask_path),
                    "source_mask_mime_type": task.source_mask_mime_type,
                }
            ),
        )
        db.add(asset)
        await db.flush()
        changed = True
    elif asset.url != task.image_url:
        asset.url = task.image_url
        asset.thumbnail_url = await ensure_thumbnail(task.image_url)
        asset.updated_at = datetime.utcnow()
        changed = True

    result = await db.execute(
        select(CanvasItem).where(
            CanvasItem.workspace_id == workspace.id,
            CanvasItem.user_id == task.user_id,
            CanvasItem.asset_id == asset.id,
            CanvasItem.task_id == task.id,
            CanvasItem.item_type == "image",
            CanvasItem.deleted_at.is_(None),
        )
    )
    result_item = result.scalar_one_or_none()
    if result_item is None:
        # 局部修改的结果应当贴近原图，便于用户在画布上比较修改前后；
        # 普通生成仍沿用任务节点作为结果落点，保留现有画布节奏。
        anchor = (source_items[-1] if task.source_mask_path and source_items else None) or task_item or (source_items[-1] if source_items else None)
        result_item = CanvasItem(
            workspace_id=workspace.id,
            user_id=task.user_id,
            asset_id=asset.id,
            task_id=task.id,
            item_type="image",
            x=(anchor.x + anchor.width + 80) if anchor else 360,
            y=anchor.y if anchor else 120,
            width=260,
            height=220,
            title=asset.title,
            data_json=json_dumps(
                {
                    "source": "studio_generation",
                    "prompt": task.prompt,
                    "tool": "local_edit" if task.source_mask_path else None,
                    "has_mask": bool(task.source_mask_path),
                }
            ),
        )
        db.add(result_item)
        await db.flush()
        changed = True

    relations: list[CanvasRelation] = []
    relation_sources = [item for item in source_items if item.id != result_item.id]
    if task_item is not None and task_item.id != result_item.id:
        relation_sources.append(task_item)

    for source_item in relation_sources:
        relation_type = "variant_of" if source_item.id == task.canvas_item_id else _relation_type_for_source(task, source_item)
        result = await db.execute(
            select(CanvasRelation).where(
                CanvasRelation.workspace_id == workspace.id,
                CanvasRelation.user_id == task.user_id,
                CanvasRelation.source_item_id == source_item.id,
                CanvasRelation.target_item_id == result_item.id,
                CanvasRelation.relation_type == relation_type,
                CanvasRelation.deleted_at.is_(None),
            )
        )
        relation = result.scalar_one_or_none()
        if relation is None:
            relation = CanvasRelation(
                workspace_id=workspace.id,
                user_id=task.user_id,
                source_item_id=source_item.id,
                target_item_id=result_item.id,
                relation_type=relation_type,
                label=_relation_label(relation_type),
                strength=1,
                data_json=json_dumps(
                    {
                        "task_id": task.id,
                        "has_mask": bool(task.source_mask_path and relation_type == "edit_source"),
                        "source_mask_mime_type": task.source_mask_mime_type if relation_type == "edit_source" else None,
                    }
                ),
            )
            db.add(relation)
            await db.flush()
            changed = True
        relations.append(relation)

    if changed:
        touch_canvas(workspace)

    return {
        "asset": asset,
        "result_item": result_item,
        "task_item": task_item,
        "relations": relations,
        "changed": changed,
    }
