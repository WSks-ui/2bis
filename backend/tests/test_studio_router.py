import unittest
from io import BytesIO
from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import UploadFile
from PIL import Image
from starlette.datastructures import Headers
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import CanvasItem, CanvasRelation, GenerateHistory, GenerationTask, GenerationTaskStatus, User, WorkspaceAsset
from app.routers.studio import (
    bulk_update_canvas_items,
    create_local_edit_task,
    create_canvas_item,
    create_canvas_relation,
    create_workspace,
    delete_asset,
    delete_canvas_item,
    generate_from_studio,
    get_canvas,
    import_history_asset,
)
from app.schemas import (
    CanvasBulkUpdateRequest,
    CanvasItemBulkPatch,
    CanvasItemCreate,
    CanvasRelationCreate,
    HistoryImportRequest,
    StudioGenerateRequest,
    WorkspaceCreate,
)
from app.services.studio_settlement import settle_studio_task_result


def png_bytes(size: tuple[int, int] = (16, 16), color=(120, 140, 160, 255)) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def mask_png_bytes(size: tuple[int, int] = (16, 16), editable: bool = True) -> bytes:
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    if editable:
        for x in range(size[0] // 4, max(size[0] // 4 + 1, size[0] // 2)):
            for y in range(size[1] // 4, max(size[1] // 4 + 1, size[1] // 2)):
                image.putpixel((x, y), (255, 255, 255, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def upload_png(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers=Headers({"content-type": "image/png"}))


class StudioRouterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def create_user(self) -> User:
        async with self.session_factory() as db:
            user = User(
                username=f"user-{datetime.utcnow().timestamp()}",
                hashed_password="x",
                free_points=20,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user

    async def create_workspace_for(self, user: User, name: str = "视觉项目"):
        async with self.session_factory() as db:
            return await create_workspace(
                WorkspaceCreate(name=name),
                db=db,
                current_user=user,
            )

    async def test_workspace_canvas_item_relation_roundtrip(self) -> None:
        user = await self.create_user()
        workspace = await self.create_workspace_for(user)

        async with self.session_factory() as db:
            prompt = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(
                    item_type="prompt",
                    title="主提示词",
                    x=10,
                    y=20,
                    data={"text": "cinematic portrait"},
                ),
                db=db,
                current_user=user,
            )
            note = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(
                    item_type="note",
                    title="风格备注",
                    x=320,
                    y=40,
                    data={"text": "保持冷暖对比"},
                ),
                db=db,
                current_user=user,
            )
            relation = await create_canvas_relation(
                workspace.id,
                CanvasRelationCreate(
                    source_item_id=note.id,
                    target_item_id=prompt.id,
                    relation_type="note_for",
                    label="说明",
                ),
                db=db,
                current_user=user,
            )
            canvas = await get_canvas(workspace.id, db=db, current_user=user)

        self.assertEqual(len(canvas.items), 2)
        self.assertEqual(len(canvas.relations), 1)
        self.assertEqual(relation.source_item_id, note.id)
        self.assertGreater(canvas.revision, 0)

    async def test_bulk_update_rejects_stale_revision(self) -> None:
        user = await self.create_user()
        workspace = await self.create_workspace_for(user)

        async with self.session_factory() as db:
            item = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(item_type="note", title="n", data={"text": "old"}),
                db=db,
                current_user=user,
            )

        async with self.session_factory() as db:
            with self.assertRaises(Exception) as ctx:
                await bulk_update_canvas_items(
                    workspace.id,
                    CanvasBulkUpdateRequest(
                        client_revision=0,
                        items=[CanvasItemBulkPatch(id=item.id, x=42)],
                    ),
                    db=db,
                    current_user=user,
                )

        self.assertEqual(getattr(ctx.exception, "status_code", None), 409)

    async def test_history_import_reuses_asset_and_can_place_multiple_items(self) -> None:
        user = await self.create_user()
        workspace = await self.create_workspace_for(user)
        async with self.session_factory() as db:
            history = GenerateHistory(
                user_id=user.id,
                prompt="a poster",
                image_url="/static/images/1/poster.png",
                quality="low",
                points_cost=1,
            )
            db.add(history)
            await db.commit()
            await db.refresh(history)
            history_id = history.id

        async with self.session_factory() as db:
            with patch("app.routers.studio.ensure_thumbnail", side_effect=lambda url: f"{url}.webp"):
                first = await import_history_asset(
                    workspace.id,
                    HistoryImportRequest(history_id=history_id, x=0, y=0),
                    db=db,
                    current_user=user,
                )
                second = await import_history_asset(
                    workspace.id,
                    HistoryImportRequest(history_id=history_id, x=240, y=0),
                    db=db,
                    current_user=user,
                )
                canvas = await get_canvas(workspace.id, db=db, current_user=user)

        self.assertEqual(first.asset.id, second.asset.id)
        self.assertEqual(len(canvas.assets), 1)
        self.assertEqual(len(canvas.items), 2)
        self.assertEqual(canvas.assets[0].thumbnail_url, "/static/images/1/poster.png.webp")

    async def test_deleting_item_or_asset_soft_deletes_connected_relations(self) -> None:
        user = await self.create_user()
        workspace = await self.create_workspace_for(user)

        async with self.session_factory() as db:
            asset = WorkspaceAsset(
                workspace_id=workspace.id,
                user_id=user.id,
                asset_type="image",
                source_type="upload",
                title="asset",
                url="/static/images/1/a.png",
            )
            db.add(asset)
            await db.flush()
            image_item = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(asset_id=asset.id, item_type="image", title="图"),
                db=db,
                current_user=user,
            )
            note_item = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(item_type="note", title="备注"),
                db=db,
                current_user=user,
            )
            await create_canvas_relation(
                workspace.id,
                CanvasRelationCreate(
                    source_item_id=note_item.id,
                    target_item_id=image_item.id,
                    relation_type="note_for",
                ),
                db=db,
                current_user=user,
            )
            await delete_asset(workspace.id, asset.id, db=db, current_user=user)
            canvas = await get_canvas(workspace.id, db=db, current_user=user)

        self.assertEqual([item.id for item in canvas.items], [note_item.id])
        self.assertEqual(canvas.relations, [])

        workspace = await self.create_workspace_for(user, "删除节点")
        async with self.session_factory() as db:
            first = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(item_type="note", title="a"),
                db=db,
                current_user=user,
            )
            second = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(item_type="note", title="b"),
                db=db,
                current_user=user,
            )
            await create_canvas_relation(
                workspace.id,
                CanvasRelationCreate(
                    source_item_id=first.id,
                    target_item_id=second.id,
                    relation_type="same_series",
                ),
                db=db,
                current_user=user,
            )
            await delete_canvas_item(workspace.id, first.id, db=db, current_user=user)
            canvas = await get_canvas(workspace.id, db=db, current_user=user)

        self.assertEqual([item.id for item in canvas.items], [second.id])
        self.assertEqual(canvas.relations, [])

    async def test_studio_generate_creates_task_item_and_deducts_quota(self) -> None:
        user = await self.create_user()
        workspace = await self.create_workspace_for(user)

        async with self.session_factory() as db:
            with patch("app.routers.studio.enqueue_generation_task") as enqueue:
                response = await generate_from_studio(
                    workspace.id,
                    StudioGenerateRequest(
                        prompt="a quiet product photo",
                        quality="low",
                        size="1024x1024",
                        x=180,
                        y=160,
                    ),
                    db=db,
                    current_user=user,
                )
                enqueue.assert_awaited_once_with(response.task.id)

            task = await db.get(GenerationTask, response.task.id)
            saved_user = await db.get(User, user.id)

        self.assertEqual(response.task.status, "pending")
        self.assertEqual(response.item.item_type, "task")
        self.assertEqual(task.workspace_id, workspace.id)
        self.assertEqual(task.canvas_item_id, response.item.id)
        self.assertEqual(saved_user.free_points, 19)

    async def test_local_edit_creates_masked_task_and_deducts_quota(self) -> None:
        user = await self.create_user()
        workspace = await self.create_workspace_for(user)
        source_bytes = png_bytes((16, 16))

        async with self.session_factory() as db:
            asset = WorkspaceAsset(
                workspace_id=workspace.id,
                user_id=user.id,
                asset_type="image",
                source_type="upload",
                title="source.png",
                url="/static/images/1/source.png",
                mime_type="image/png",
                width=16,
                height=16,
            )
            db.add(asset)
            await db.flush()
            image_item = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(asset_id=asset.id, item_type="image", title="源图", x=40, y=60),
                db=db,
                current_user=user,
            )

            with (
                patch("app.routers.studio._read_file_bytes", new=AsyncMock(return_value=source_bytes)),
                patch("app.routers.studio.os.path.exists", return_value=True),
                patch("app.routers.studio.enqueue_generation_task") as enqueue,
            ):
                response = await create_local_edit_task(
                    workspace.id,
                    source_item_id=image_item.id,
                    prompt="change the selected area",
                    quality="low",
                    mask=upload_png("mask.png", mask_png_bytes((16, 16))),
                    x=320,
                    y=60,
                    db=db,
                    current_user=user,
                )
                enqueue.assert_awaited_once_with(response.task.id)

            task = await db.get(GenerationTask, response.task.id)
            saved_user = await db.get(User, user.id)

        self.assertEqual(response.task.status, "pending")
        self.assertEqual(response.item.item_type, "task")
        self.assertEqual(response.item.data["tool"], "local_edit")
        self.assertEqual(task.source_mask_mime_type, "image/png")
        self.assertTrue(task.source_mask_path)
        self.assertEqual(task.studio_source_item_ids_json, f"[{image_item.id}]")
        self.assertEqual(saved_user.free_points, 19)

    async def test_local_edit_rejects_invalid_masks_without_deducting_quota(self) -> None:
        user = await self.create_user()
        workspace = await self.create_workspace_for(user)
        source_bytes = png_bytes((16, 16))

        async with self.session_factory() as db:
            asset = WorkspaceAsset(
                workspace_id=workspace.id,
                user_id=user.id,
                asset_type="image",
                source_type="upload",
                title="source.png",
                url="/static/images/1/source.png",
                mime_type="image/png",
                width=16,
                height=16,
            )
            db.add(asset)
            await db.flush()
            image_item = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(asset_id=asset.id, item_type="image", title="源图"),
                db=db,
                current_user=user,
            )
            note_item = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(item_type="note", title="备注"),
                db=db,
                current_user=user,
            )

            invalid_cases = [
                (image_item.id, mask_png_bytes((16, 16), editable=False), 400),
                (image_item.id, mask_png_bytes((12, 16)), 400),
                (note_item.id, mask_png_bytes((16, 16)), 400),
            ]
            with (
                patch("app.routers.studio._read_file_bytes", new=AsyncMock(return_value=source_bytes)),
                patch("app.routers.studio.os.path.exists", return_value=True),
            ):
                for source_item_id, mask_bytes, expected_status in invalid_cases:
                    with self.assertRaises(Exception) as ctx:
                        await create_local_edit_task(
                            workspace.id,
                            source_item_id=source_item_id,
                            prompt="change something",
                            quality="low",
                            mask=upload_png("mask.png", mask_bytes),
                            x=0,
                            y=0,
                            db=db,
                            current_user=user,
                        )
                    self.assertEqual(getattr(ctx.exception, "status_code", None), expected_status)

            saved_user = await db.get(User, user.id)

        self.assertEqual(saved_user.free_points, 20)

    async def test_local_edit_accepts_remote_source_image(self) -> None:
        user = await self.create_user()
        workspace = await self.create_workspace_for(user)
        source_bytes = png_bytes((20, 10))

        async with self.session_factory() as db:
            asset = WorkspaceAsset(
                workspace_id=workspace.id,
                user_id=user.id,
                asset_type="image",
                source_type="history_import",
                title="remote.png",
                url="https://cdn.example.test/remote.png",
                mime_type="image/png",
                width=20,
                height=10,
            )
            db.add(asset)
            await db.flush()
            image_item = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(asset_id=asset.id, item_type="image", title="远程图"),
                db=db,
                current_user=user,
            )

            def handler(request: httpx.Request) -> httpx.Response:
                return httpx.Response(200, content=source_bytes, headers={"content-type": "image/png"})

            real_async_client = httpx.AsyncClient

            def client_factory(*args, **kwargs):
                return real_async_client(transport=httpx.MockTransport(handler))

            with (
                patch("app.routers.studio.httpx.AsyncClient", side_effect=client_factory),
                patch("app.routers.studio.enqueue_generation_task") as enqueue,
            ):
                response = await create_local_edit_task(
                    workspace.id,
                    source_item_id=image_item.id,
                    prompt="edit the selected stripe",
                    quality="low",
                    mask=upload_png("mask.png", mask_png_bytes((20, 10))),
                    x=100,
                    y=100,
                    db=db,
                    current_user=user,
                )
                enqueue.assert_awaited_once_with(response.task.id)

            task = await db.get(GenerationTask, response.task.id)

        self.assertEqual(task.source_image_mime_type, "image/png")
        self.assertEqual(task.size, "1920x1080")
        self.assertTrue(task.source_mask_path)

    async def test_settle_studio_task_result_is_idempotent(self) -> None:
        user = await self.create_user()
        workspace = await self.create_workspace_for(user)

        async with self.session_factory() as db:
            prompt_item = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(item_type="prompt", title="Prompt", data={"text": "minimal poster"}),
                db=db,
                current_user=user,
            )
            task = GenerationTask(
                user_id=user.id,
                workspace_id=workspace.id,
                mode="text2img",
                prompt="minimal poster",
                quality="low",
                size="1024x1024",
                status=GenerationTaskStatus.SUCCESS,
                points_cost=1,
                balance_source="free_points",
                image_url="/static/images/1/result.png",
                studio_source_item_ids_json=f"[{prompt_item.id}]",
            )
            db.add(task)
            await db.flush()
            task_item = await create_canvas_item(
                workspace.id,
                CanvasItemCreate(
                    task_id=task.id,
                    item_type="task",
                    title="生成任务",
                    x=280,
                    y=120,
                    data={"status": "pending"},
                ),
                db=db,
                current_user=user,
            )
            task.canvas_item_id = task_item.id

            with patch("app.services.studio_settlement.ensure_thumbnail", side_effect=lambda url: f"{url}.webp"):
                await settle_studio_task_result(db, task)
                await settle_studio_task_result(db, task)
            await db.commit()

            assets = (
                await db.execute(
                    select(WorkspaceAsset).where(
                        WorkspaceAsset.workspace_id == workspace.id,
                        WorkspaceAsset.task_id == task.id,
                        WorkspaceAsset.deleted_at.is_(None),
                    )
                )
            ).scalars().all()
            result_items = (
                await db.execute(
                    select(CanvasItem).where(
                        CanvasItem.workspace_id == workspace.id,
                        CanvasItem.task_id == task.id,
                        CanvasItem.item_type == "image",
                        CanvasItem.deleted_at.is_(None),
                    )
                )
            ).scalars().all()
            relations = (
                await db.execute(
                    select(CanvasRelation).where(
                        CanvasRelation.workspace_id == workspace.id,
                        CanvasRelation.target_item_id == result_items[0].id,
                        CanvasRelation.deleted_at.is_(None),
                    )
                )
            ).scalars().all()

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].thumbnail_url, "/static/images/1/result.png.webp")
        self.assertEqual(len(result_items), 1)
        self.assertEqual({relation.source_item_id for relation in relations}, {prompt_item.id, task_item.id})


if __name__ == "__main__":
    unittest.main()
