import os
import uuid

from app.config import UPLOAD_DIR


async def save_upload_file(file_bytes: bytes, user_id: int, original_filename: str | None) -> str:
    ext = "png"
    if original_filename and "." in original_filename:
        candidate = original_filename.rsplit(".", 1)[1].lower()
        if candidate in {"png", "jpg", "jpeg", "webp"}:
            ext = "jpg" if candidate == "jpeg" else candidate

    user_dir = os.path.join(UPLOAD_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    path = os.path.join(user_dir, f"{uuid.uuid4().hex}.{ext}")

    def write_file() -> None:
        with open(path, "wb") as f:
            f.write(file_bytes)

    import asyncio

    await asyncio.to_thread(write_file)
    return path


async def read_upload_file(path: str) -> bytes:
    import asyncio

    def read_file() -> bytes:
        with open(path, "rb") as f:
            return f.read()

    return await asyncio.to_thread(read_file)
