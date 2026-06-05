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
