from __future__ import annotations

import asyncio
import os
from pathlib import Path

from PIL import Image, ImageOps

from app.config import IMAGE_DIR, IMAGE_URL_PREFIX


THUMBNAIL_LONG_EDGE = 640
THUMBNAIL_QUALITY = 72
THUMBNAIL_DIR_NAME = "_thumbs"


def _safe_source_path(image_url: str | None) -> Path | None:
    if not image_url or not image_url.startswith(f"{IMAGE_URL_PREFIX}/"):
        return None

    relative_url = image_url.removeprefix(f"{IMAGE_URL_PREFIX}/").lstrip("/")
    source_path = (Path(IMAGE_DIR) / relative_url).resolve()
    image_root = Path(IMAGE_DIR).resolve()

    try:
        source_path.relative_to(image_root)
    except ValueError:
        return None

    if not source_path.is_file():
        return None
    return source_path


def _thumbnail_path_for(source_path: Path) -> Path:
    image_root = Path(IMAGE_DIR).resolve()
    relative_source = source_path.resolve().relative_to(image_root)
    user_part = relative_source.parent
    return image_root / THUMBNAIL_DIR_NAME / user_part / f"{source_path.stem}.webp"


def _thumbnail_url_for(thumbnail_path: Path) -> str:
    relative_thumb = thumbnail_path.resolve().relative_to(Path(IMAGE_DIR).resolve())
    return f"{IMAGE_URL_PREFIX}/{relative_thumb.as_posix()}"


def _ensure_thumbnail_sync(image_url: str | None) -> str | None:
    source_path = _safe_source_path(image_url)
    if source_path is None:
        return image_url

    thumbnail_path = _thumbnail_path_for(source_path)
    if thumbnail_path.exists() and thumbnail_path.stat().st_mtime >= source_path.stat().st_mtime:
        return _thumbnail_url_for(thumbnail_path)

    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((THUMBNAIL_LONG_EDGE, THUMBNAIL_LONG_EDGE), Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        image.save(thumbnail_path, "WEBP", quality=THUMBNAIL_QUALITY, method=4)

    return _thumbnail_url_for(thumbnail_path)


def _delete_thumbnail_sync(image_url: str | None) -> None:
    source_path = _safe_source_path(image_url)
    if source_path is None:
        return

    thumbnail_path = _thumbnail_path_for(source_path)
    try:
        if thumbnail_path.exists():
            os.remove(thumbnail_path)
    except OSError:
        pass


async def ensure_thumbnail(image_url: str | None) -> str | None:
    return await asyncio.to_thread(_ensure_thumbnail_sync, image_url)


async def delete_thumbnail(image_url: str | None) -> None:
    await asyncio.to_thread(_delete_thumbnail_sync, image_url)
