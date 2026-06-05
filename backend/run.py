import os

import uvicorn

from app.config import UVICORN_WORKERS

if __name__ == "__main__":
    # 多 worker 需要配合 PostgreSQL (SQLite 多进程写会冲突)
    # Windows 不支持 uvicorn 的 fork 模式,workers>1 时会自动退化为 1
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
        workers=max(1, UVICORN_WORKERS),
    )
