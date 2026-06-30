import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import IMAGE_DIR
from app.database import init_db
from app.routers import admin, auth, points, membership, generate, payment, history, edits, studio
from app.services.ai_client import close_client
from app.services.task_queue import close_redis

app = FastAPI(title="AI Image Generator")


class CachedStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers.setdefault("Cache-Control", "public, max-age=2592000, immutable")
        return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 把生成的图片目录挂成静态资源,前端可直接用 <img src="/static/images/...">
os.makedirs(IMAGE_DIR, exist_ok=True)
app.mount("/static/images", CachedStaticFiles(directory=IMAGE_DIR), name="static_images")


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    await close_client()
    await close_redis()


app.include_router(auth.router, prefix="/api")
app.include_router(points.router, prefix="/api")
app.include_router(membership.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(payment.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(edits.router, prefix="/api")
app.include_router(studio.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
