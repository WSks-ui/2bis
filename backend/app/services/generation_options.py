from __future__ import annotations

import re
from copy import deepcopy


MAX_IMAGE_LONG_EDGE = 3840
MAX_IMAGE_PIXELS = 8_294_400
MIN_IMAGE_EDGE = 64
ALLOWED_UPLOAD_MIME_TYPES = ("image/png", "image/jpeg", "image/webp")
UPLOAD_MIME_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


QUALITY_OPTIONS: list[dict] = [
    {"label": "低质量", "value": "low"},
    {"label": "中质量", "value": "medium"},
    {"label": "高质量", "value": "high"},
]


IMAGE_SIZE_GROUPS: list[dict] = [
    {
        "ratio": "21:9",
        "name": "超宽银幕",
        "sizes": [
            {"label": "影院高清", "value": "3584x1536"},
            {"label": "超宽标准", "value": "2688x1152"},
            {"label": "超宽轻量", "value": "1792x768"},
        ],
    },
    {
        "ratio": "16:9",
        "name": "横版宽屏",
        "sizes": [
            {"label": "4K 宽屏", "value": "3840x2160"},
            {"label": "高清宽屏", "value": "2560x1440"},
            {"label": "标准宽屏", "value": "1920x1080"},
            {"label": "轻量宽屏", "value": "1344x768"},
        ],
    },
    {
        "ratio": "3:2",
        "name": "相机横幅",
        "sizes": [
            {"label": "高清横幅", "value": "3456x2304"},
            {"label": "标准横幅", "value": "2304x1536"},
            {"label": "轻量横幅", "value": "1728x1152"},
        ],
    },
    {
        "ratio": "4:3",
        "name": "经典横图",
        "sizes": [
            {"label": "高清横图", "value": "3072x2304"},
            {"label": "标准横图", "value": "2048x1536"},
            {"label": "轻量横图", "value": "1536x1152"},
            {"label": "平台轻量", "value": "1152x896"},
        ],
    },
    {
        "ratio": "1:1",
        "name": "方图",
        "sizes": [
            {"label": "高清方图", "value": "2048x2048"},
            {"label": "标准方图", "value": "1536x1536"},
            {"label": "轻量方图", "value": "1024x1024"},
        ],
    },
    {
        "ratio": "3:4",
        "name": "经典竖图",
        "sizes": [
            {"label": "高清竖图", "value": "2304x3072"},
            {"label": "平台竖图", "value": "1792x2304"},
            {"label": "标准竖图", "value": "1536x2048"},
            {"label": "轻量竖图", "value": "1152x1536"},
            {"label": "平台轻量", "value": "896x1152"},
        ],
    },
    {
        "ratio": "2:3",
        "name": "海报竖图",
        "sizes": [
            {"label": "高清海报", "value": "2304x3456"},
            {"label": "标准海报", "value": "1536x2304"},
            {"label": "轻量海报", "value": "1152x1728"},
        ],
    },
    {
        "ratio": "9:16",
        "name": "移动竖屏",
        "sizes": [
            {"label": "4K 竖屏", "value": "2160x3840"},
            {"label": "高清竖屏", "value": "1440x2560"},
            {"label": "标准竖屏", "value": "1080x1920"},
            {"label": "轻量竖屏", "value": "720x1280"},
        ],
    },
]


class GenerationOptionsError(ValueError):
    pass


class GenerationOptions:
    _size_pattern = re.compile(r"^([1-9]\d{1,4})x([1-9]\d{1,4})$")
    _allowed_qualities = {item["value"] for item in QUALITY_OPTIONS}
    _allowed_sizes = {
        size["value"]
        for group in IMAGE_SIZE_GROUPS
        for size in group["sizes"]
    }

    @staticmethod
    def get_quality_options() -> list[dict]:
        return deepcopy(QUALITY_OPTIONS)

    @staticmethod
    def get_image_size_groups() -> list[dict]:
        return deepcopy(IMAGE_SIZE_GROUPS)

    @staticmethod
    def get_constraints() -> dict:
        return {
            "max_long_edge": MAX_IMAGE_LONG_EDGE,
            "max_pixels": MAX_IMAGE_PIXELS,
            "min_edge": MIN_IMAGE_EDGE,
            "allowed_upload_mime_types": list(ALLOWED_UPLOAD_MIME_TYPES),
        }

    @classmethod
    def normalize_quality(cls, quality: str | None) -> str:
        normalized = (quality or "low").strip().lower()
        if normalized not in cls._allowed_qualities:
            raise GenerationOptionsError("Invalid quality")
        return normalized

    @classmethod
    def normalize_size(cls, size: str | None) -> str:
        normalized = (size or "1024x1024").strip().lower().replace("×", "x")
        width, height = cls.parse_size(normalized)
        if normalized not in cls._allowed_sizes:
            raise GenerationOptionsError("Invalid image size")
        cls.validate_dimensions(width, height)
        return normalized

    @classmethod
    def parse_size(cls, size: str) -> tuple[int, int]:
        match = cls._size_pattern.match(size)
        if not match:
            raise GenerationOptionsError("Invalid image size")
        return int(match.group(1)), int(match.group(2))

    @staticmethod
    def validate_dimensions(width: int, height: int) -> None:
        if width < MIN_IMAGE_EDGE or height < MIN_IMAGE_EDGE:
            raise GenerationOptionsError("Image size is too small")
        if max(width, height) > MAX_IMAGE_LONG_EDGE:
            raise GenerationOptionsError(
                f"Image longest edge must be <= {MAX_IMAGE_LONG_EDGE}px"
            )
        if width * height > MAX_IMAGE_PIXELS:
            raise GenerationOptionsError(
                f"Image pixels must be <= {MAX_IMAGE_PIXELS}"
            )

    @staticmethod
    def detect_upload_mime(file_bytes: bytes) -> str | None:
        if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if file_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if (
            len(file_bytes) >= 12
            and file_bytes[:4] == b"RIFF"
            and file_bytes[8:12] == b"WEBP"
        ):
            return "image/webp"
        return None

    @classmethod
    def validate_upload_image(cls, file_bytes: bytes, content_type: str | None) -> str:
        detected = cls.detect_upload_mime(file_bytes)
        if detected is None:
            raise GenerationOptionsError("Invalid image file")

        claimed = (content_type or "").split(";", 1)[0].strip().lower()
        if claimed and claimed not in ALLOWED_UPLOAD_MIME_TYPES:
            raise GenerationOptionsError("Unsupported image file type")
        if claimed and claimed != detected:
            raise GenerationOptionsError("Image file type does not match content")
        return detected

    @staticmethod
    def extension_for_mime(mime_type: str | None) -> str:
        return UPLOAD_MIME_EXTENSIONS.get(mime_type or "", "png")
