import asyncio
import base64
import os
import re
import uuid

import boto3

from app.config import (
    IMAGE_DIR,
    IMAGE_URL_PREFIX,
    S3_ACCESS_KEY_ID,
    S3_BUCKET,
    S3_ENDPOINT_URL,
    S3_PUBLIC_BASE_URL,
    S3_REGION,
    S3_SECRET_ACCESS_KEY,
    STORAGE_BACKEND,
)


def _parse_data_url(data_url: str) -> tuple[str, bytes] | None:
    if not data_url:
        return None
    match = re.match(r"^data:image/(png|jpeg|jpg|webp);base64,(.+)$", data_url, re.DOTALL)
    if not match:
        return None
    fmt = "jpg" if match.group(1) == "jpeg" else match.group(1)
    return fmt, base64.b64decode(match.group(2))


def _save_local(data_url: str, user_id: int) -> str:
    parsed = _parse_data_url(data_url)
    if parsed is None:
        return data_url

    fmt, image_bytes = parsed
    user_dir = os.path.join(IMAGE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{fmt}"
    abs_path = os.path.join(user_dir, filename)

    with open(abs_path, "wb") as f:
        f.write(image_bytes)

    return f"{IMAGE_URL_PREFIX}/{user_id}/{filename}"


def _save_s3(data_url: str, user_id: int) -> str:
    parsed = _parse_data_url(data_url)
    if parsed is None:
        return data_url
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")

    fmt, image_bytes = parsed
    key = f"images/{user_id}/{uuid.uuid4().hex}.{fmt}"
    client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL or None,
        aws_access_key_id=S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY or None,
        region_name=S3_REGION or None,
    )
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType=f"image/{'jpeg' if fmt == 'jpg' else fmt}",
    )
    if S3_PUBLIC_BASE_URL:
        return f"{S3_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    return f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"


def _save_sync(data_url: str, user_id: int) -> str:
    if not data_url:
        return ""
    if data_url.startswith("http://") or data_url.startswith("https://"):
        return data_url
    if STORAGE_BACKEND.lower() == "s3":
        return _save_s3(data_url, user_id)
    return _save_local(data_url, user_id)


async def save_data_url(data_url: str, user_id: int) -> str:
    return await asyncio.to_thread(_save_sync, data_url, user_id)
