import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app.services import image_derivatives


class ImageDerivativesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    async def asyncTearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_generates_webp_thumbnail_for_local_image(self) -> None:
        source_dir = Path(self.temp_dir) / "1"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_path = source_dir / "source.png"
        Image.new("RGB", (1200, 800), "#336699").save(source_path)

        with patch.object(image_derivatives, "IMAGE_DIR", self.temp_dir):
            thumbnail_url = await image_derivatives.ensure_thumbnail("/static/images/1/source.png")

        self.assertEqual(thumbnail_url, "/static/images/_thumbs/1/source.webp")
        thumbnail_path = Path(self.temp_dir) / "_thumbs" / "1" / "source.webp"
        self.assertTrue(thumbnail_path.exists())
        with Image.open(thumbnail_path) as thumbnail:
            self.assertLessEqual(max(thumbnail.size), image_derivatives.THUMBNAIL_LONG_EDGE)

    async def test_returns_remote_url_without_thumbnail_generation(self) -> None:
        url = "https://cdn.example.com/image.png"

        with patch.object(image_derivatives, "IMAGE_DIR", self.temp_dir):
            thumbnail_url = await image_derivatives.ensure_thumbnail(url)

        self.assertEqual(thumbnail_url, url)
        self.assertFalse((Path(self.temp_dir) / "_thumbs").exists())


if __name__ == "__main__":
    unittest.main()
