import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./aigen.db")
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
AI_API_URL: str = os.getenv("AI_API_URL", "https://www.aiartmirror.com/v1")
AI_API_KEY: str = os.getenv("AI_API_KEY", "")
AI_TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "120"))
AI_MAX_CONCURRENT: int = int(os.getenv("AI_MAX_CONCURRENT", "1000"))
# 编辑接口上传图片上限 (20MB),超过拒绝避免 OOM
MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(20 * 1024 * 1024)))
# AI 生成图保存目录 (相对项目根),URL 前缀为 /static/images
IMAGE_DIR: str = os.getenv("IMAGE_DIR", "static/images")
IMAGE_URL_PREFIX: str = os.getenv("IMAGE_URL_PREFIX", "/static/images")
# httpx 连接池配置
HTTP_MAX_CONNECTIONS: int = int(os.getenv("HTTP_MAX_CONNECTIONS", "200"))
HTTP_MAX_KEEPALIVE: int = int(os.getenv("HTTP_MAX_KEEPALIVE", "50"))
# uvicorn worker 数 (多进程,需要配合 PostgreSQL 避免 SQLite 写锁冲突)
UVICORN_WORKERS: int = int(os.getenv("UVICORN_WORKERS", "1"))
