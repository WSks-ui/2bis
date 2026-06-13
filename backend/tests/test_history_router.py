import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import GenerateHistory, User
from app.routers.history import list_history


class HistoryRouterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_list_history_returns_paginated_filtered_records(self) -> None:
        now = datetime.utcnow()
        async with self.session_factory() as db:
            user = User(username="u", hashed_password="x")
            db.add(user)
            await db.flush()
            for index in range(5):
                db.add(
                    GenerateHistory(
                        user_id=user.id,
                        prompt=f"p{index}",
                        image_url=f"/static/images/{user.id}/{index}.png",
                        quality="high" if index % 2 else "low",
                        points_cost=3,
                        balance_source="quota",
                        workflow_type="professional" if index % 2 else "standard",
                        created_at=now - timedelta(minutes=index),
                    )
                )
            await db.commit()
            user_id = user.id

        async with self.session_factory() as db:
            current_user = await db.get(User, user_id)
            with patch("app.routers.history.ensure_thumbnail", side_effect=lambda url: f"{url}.webp"):
                page = await list_history(
                    page=1,
                    page_size=2,
                    workflow="standard",
                    db=db,
                    current_user=current_user,
                )

        self.assertEqual(page.total, 3)
        self.assertEqual(page.page, 1)
        self.assertEqual(page.page_size, 2)
        self.assertEqual(page.total_pages, 2)
        self.assertEqual(len(page.records), 2)
        self.assertTrue(all(record.workflow_type == "standard" for record in page.records))
        self.assertTrue(page.records[0].thumbnail_url.endswith(".webp"))


if __name__ == "__main__":
    unittest.main()
