"""AI 生成图落盘工具.

将 base64 data URL 写入本地文件,返回可访问的 HTTP URL.
避免大体积 base64 直接塞进数据库 (单图 1-3MB,数百用户会膨胀到几百 MB).
"""
import asyncio
import base64
import os
import re
import uuid

from app.config import IMAGE_DIR, IMAGE_URL_PREFIX


def _save_sync(data_url: str, user_id: int) -> str:
    """同步落盘实现,被 to_thread 调用."""
    if not data_url:
        return ""

    if data_url.startswith("http://") or data_url.startswith("https://"):
        return data_url

    match = re.match(r"^data:image/(png|jpeg|jpg|webp);base64,(.+)$", data_url, re.DOTALL)
    if not match:
        return data_url

    fmt = "jpg" if match.group(1) == "jpeg" else match.group(1)
    b64_payload = match.group(2)

    user_dir = os.path.join(IMAGE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{fmt}"
    abs_path = os.path.join(user_dir, filename)

    with open(abs_path, "wb") as f:
        f.write(base64.b64decode(b64_payload))

    return f"{IMAGE_URL_PREFIX}/{user_id}/{filename}"


async def save_data_url(data_url: str, user_id: int) -> str:
    """解析 data URL 并保存到 IMAGE_DIR/{user_id}/{uuid}.png, 返回 /static/... URL.

    文件写入放到线程池执行,避免 1-3MB 的同步 I/O 阻塞事件循环.
    """
    return await asyncio.to_thread(_save_sync, data_url, user_id)
