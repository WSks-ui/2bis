import asyncio
import os

import uvicorn

from app.config import UVICORN_WORKERS
from worker import main as worker_main


async def main():
    reload = os.getenv("RELOAD", "false").lower() in ("true", "1", "yes")
    config = uvicorn.Config(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=reload,
        workers=1 if reload else max(1, UVICORN_WORKERS),
    )
    server = uvicorn.Server(config)

    worker = asyncio.create_task(worker_main())
    try:
        await server.serve()
    finally:
        worker.cancel()


if __name__ == "__main__":
    asyncio.run(main())
