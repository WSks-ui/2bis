import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import IMAGE_DIR
from app.database import init_db
from app.routers import auth, points, membership, generate, payment, history, edits
from app.services.ai_client import close_client

app = FastAPI(title="AI Image Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 把生成的图片目录挂成静态资源,前端可直接用 <img src="/static/images/...">
os.makedirs(IMAGE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.dirname(IMAGE_DIR) or "."), name="static")


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    # 关闭复用的 httpx client,释放连接池
    await close_client()


app.include_router(auth.router, prefix="/api")
app.include_router(points.router, prefix="/api")
app.include_router(membership.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(payment.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(edits.router, prefix="/api")
