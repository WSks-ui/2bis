import unittest
from app.services.generation_options import (
    GenerationOptions,
    GenerationOptionsError,
    MAX_IMAGE_LONG_EDGE,
    MAX_IMAGE_PIXELS,
)


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
)


class GenerationOptionsTest(unittest.TestCase):
    def test_all_advertised_sizes_fit_api_constraints(self) -> None:
        for group in GenerationOptions.get_image_size_groups():
            for size in group["sizes"]:
                width, height = GenerationOptions.parse_size(size["value"])
                self.assertLessEqual(max(width, height), MAX_IMAGE_LONG_EDGE, size)
                self.assertLessEqual(width * height, MAX_IMAGE_PIXELS, size)
                self.assertEqual(GenerationOptions.normalize_size(size["value"]), size["value"])

    def test_rejects_long_edge_that_exceeds_provider_limit(self) -> None:
        with self.assertRaises(GenerationOptionsError):
            GenerationOptions.normalize_size("4032x1728")

    def test_rejects_size_that_is_not_advertised(self) -> None:
        with self.assertRaises(GenerationOptionsError):
            GenerationOptions.normalize_size("1280x720")

    def test_rejects_unknown_quality(self) -> None:
        with self.assertRaises(GenerationOptionsError):
            GenerationOptions.normalize_quality("ultra")

    def test_validates_upload_magic_bytes(self) -> None:
        self.assertEqual(
            GenerationOptions.validate_upload_image(PNG_BYTES, "image/png"),
            "image/png",
        )

        with self.assertRaises(GenerationOptionsError):
            GenerationOptions.validate_upload_image(b"not an image", "image/png")

    def test_rejects_upload_content_type_mismatch(self) -> None:
        with self.assertRaises(GenerationOptionsError):
            GenerationOptions.validate_upload_image(PNG_BYTES, "image/jpeg")


if __name__ == "__main__":
    unittest.main()
