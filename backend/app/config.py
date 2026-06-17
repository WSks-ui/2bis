import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./aigen.db")
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
ADMIN_USERNAMES: set[str] = {
    username.strip()
    for username in os.getenv("ADMIN_USERNAMES", "").split(",")
    if username.strip()
}
API_KEY_ENCRYPTION_SECRET: str = os.getenv("API_KEY_ENCRYPTION_SECRET", "")
API_KEY_CONFIG_CACHE_SECONDS: float = float(os.getenv("API_KEY_CONFIG_CACHE_SECONDS", "5"))
API_KEY_CIRCUIT_FAILURE_THRESHOLD: int = int(os.getenv("API_KEY_CIRCUIT_FAILURE_THRESHOLD", "3"))
API_KEY_CIRCUIT_COOLDOWN_SECONDS: int = int(os.getenv("API_KEY_CIRCUIT_COOLDOWN_SECONDS", "600"))
API_KEY_PROBE_TIMEOUT: float = float(os.getenv("API_KEY_PROBE_TIMEOUT", "360"))
API_KEY_ALLOW_ENV_FALLBACK: bool = os.getenv("API_KEY_ALLOW_ENV_FALLBACK", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
AI_API_URL: str = os.getenv("AI_API_URL", "https://www.aiartmirror.com/v1")
AI_API_KEY: str = os.getenv("AI_API_KEY", "")
AI_TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "2400"))
AI_RESPONSE_BODY_TIMEOUT: int = int(os.getenv("AI_RESPONSE_BODY_TIMEOUT", "900"))
_AI_IMAGE_RESPONSE_FORMAT_RAW: str = os.getenv("AI_IMAGE_RESPONSE_FORMAT", "").strip().lower()
if _AI_IMAGE_RESPONSE_FORMAT_RAW in {"", "auto", "none", "off", "disabled", "false"}:
    AI_IMAGE_RESPONSE_FORMAT = ""
else:
    AI_IMAGE_RESPONSE_FORMAT = _AI_IMAGE_RESPONSE_FORMAT_RAW
AI_RESPONSE_FORMAT_FALLBACK: bool = os.getenv("AI_RESPONSE_FORMAT_FALLBACK", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
AI_MAX_CONCURRENT: int = int(os.getenv("AI_MAX_CONCURRENT", "2"))
AI_MIN_REQUEST_INTERVAL_SECONDS: float = float(os.getenv("AI_MIN_REQUEST_INTERVAL_SECONDS", "1.0"))
AI_RATE_LIMIT_MAX_RETRIES: int = int(os.getenv("AI_RATE_LIMIT_MAX_RETRIES", "6"))
AI_RATE_LIMIT_RETRY_DELAY_SECONDS: float = float(os.getenv("AI_RATE_LIMIT_RETRY_DELAY_SECONDS", "1.0"))
AI_RATE_LIMIT_MIN_RETRY_DELAY_SECONDS: float = float(os.getenv("AI_RATE_LIMIT_MIN_RETRY_DELAY_SECONDS", "2.0"))
MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(20 * 1024 * 1024)))
IMAGE_DIR: str = os.getenv("IMAGE_DIR", "static/images")
IMAGE_URL_PREFIX: str = os.getenv("IMAGE_URL_PREFIX", "/static/images")
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "static/uploads")
HTTP_MAX_CONNECTIONS: int = int(os.getenv("HTTP_MAX_CONNECTIONS", "10"))
HTTP_MAX_KEEPALIVE: int = int(os.getenv("HTTP_MAX_KEEPALIVE", "5"))
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
UVICORN_WORKERS: int = int(os.getenv("UVICORN_WORKERS", "1"))
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GENERATION_QUEUE_NAME: str = os.getenv("GENERATION_QUEUE_NAME", "generation_tasks")
GENERATION_WORKER_CONCURRENCY: int = int(os.getenv("GENERATION_WORKER_CONCURRENCY", "2"))
GENERATION_POLL_INTERVAL: float = float(os.getenv("GENERATION_POLL_INTERVAL", "1"))
GENERATION_MAX_RETRIES: int = int(os.getenv("GENERATION_MAX_RETRIES", "2"))
GENERATION_TASK_TIMEOUT: int = int(os.getenv("GENERATION_TASK_TIMEOUT", "3600"))
GENERATION_PROCESSING_RECOVERY_SECONDS: int = int(os.getenv("GENERATION_PROCESSING_RECOVERY_SECONDS", "3900"))
STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")
S3_ACCESS_KEY_ID: str = os.getenv("S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY: str = os.getenv("S3_SECRET_ACCESS_KEY", "")
S3_BUCKET: str = os.getenv("S3_BUCKET", "")
S3_REGION: str = os.getenv("S3_REGION", "auto")
S3_PUBLIC_BASE_URL: str = os.getenv("S3_PUBLIC_BASE_URL", "")

# 每日签到奖励规则: 连续第N天 → 奖励积分
CHECKIN_REWARDS: dict = {1: 1, 2: 1, 3: 1, 4: 2, 5: 1, 6: 1, 7: 3}
# 免费积分有效期 (天)
FREE_POINTS_TTL_DAYS: int = int(os.getenv("FREE_POINTS_TTL_DAYS", "10"))

TRIAL_PACK: dict = {
    "id": 1,
    "name": "Trial Pack",
    "price": 5.0,
    "quota": 30,
    "duration_days": 7,
    "trial_high_quality_limit": 0,
}

SUBSCRIPTION_PLANS: list[dict] = [
    {
        "id": 1,
        "name": "Light",
        "plan_key": "light",
        "monthly_price": 29.0,
        "yearly_price": 268.0,
        "monthly_quota": 100,
    },
    {
        "id": 2,
        "name": "Creator",
        "plan_key": "creator",
        "monthly_price": 69.0,
        "yearly_price": 628.0,
        "monthly_quota": 350,
    },
    {
        "id": 3,
        "name": "Pro",
        "plan_key": "pro",
        "monthly_price": 149.0,
        "yearly_price": 1368.0,
        "monthly_quota": 800,
    },
]

QUOTA_COST: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
}

EXPERIENCE_POINTS_QUALITIES: set[str] = {"low", "medium"}
STANDARD_WORKFLOW_TYPE: str = "standard"
DEFAULT_WORKFLOW_TYPE: str = os.getenv("DEFAULT_WORKFLOW_TYPE", STANDARD_WORKFLOW_TYPE).strip().lower() or STANDARD_WORKFLOW_TYPE
WORKFLOW_QUOTA_COST: dict[str, dict[str, int]] = {
    STANDARD_WORKFLOW_TYPE: QUOTA_COST,
    "professional": {
        "low": int(os.getenv("PROFESSIONAL_WORKFLOW_LOW_COST", str(QUOTA_COST["low"]))),
        "medium": int(os.getenv("PROFESSIONAL_WORKFLOW_MEDIUM_COST", str(QUOTA_COST["medium"]))),
        "high": int(os.getenv("PROFESSIONAL_WORKFLOW_HIGH_COST", str(QUOTA_COST["high"]))),
    },
}

WORKFLOW_PRESETS: list[dict] = [
    {
        "workflow_type": STANDARD_WORKFLOW_TYPE,
        "workflow_preset": None,
        "name": "标准生成",
        "description": "适合日常出图，低/中质量优先使用体验积分。",
    },
    {
        "workflow_type": "professional",
        "workflow_preset": "pro-detail",
        "name": "专业工作流",
        "description": "用于更严格的成片质量测试，统一消耗订阅额度。",
    },
]
