"""Regression tests for Rust subsystem image extraction."""

import base64
import os
import tempfile
import unittest
from pathlib import Path

from rust_subsystem import RustParallelSubsystem


SAMPLE_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+i3xQAAAAASUVORK5CYII="
)


class RustSubsystemImageExtractionTests(unittest.TestCase):
    def _with_production_runtime(self) -> RustParallelSubsystem:
        previous_runtime = os.environ.get("EDISON_RUNTIME_PROFILE")
        os.environ["EDISON_RUNTIME_PROFILE"] = "production"
        self.addCleanup(self._restore_runtime, previous_runtime)

        subsystem = RustParallelSubsystem()
        if not subsystem.native_available:
            self.skipTest("Native Rust extension is not installed")
        return subsystem

    @staticmethod
    def _restore_runtime(previous_runtime: str | None) -> None:
        if previous_runtime is None:
            os.environ.pop("EDISON_RUNTIME_PROFILE", None)
        else:
            os.environ["EDISON_RUNTIME_PROFILE"] = previous_runtime

    def test_extract_image_folder_pages_returns_native_payload(self) -> None:
        subsystem = self._with_production_runtime()

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.png"
            image_path.write_bytes(base64.b64decode(SAMPLE_PNG_BASE64))

            payload = subsystem.extract_image_folder_pages(temp_dir, use_markitdown=False)

            self.assertEqual(payload.get("backend"), "rust-native")
            self.assertEqual(payload.get("image_count"), 1)
            self.assertEqual(payload.get("parallel_backend"), "rust-native")

            page_data = payload.get("page_data", [])
            self.assertEqual(len(page_data), 1)
            self.assertEqual(page_data[0].get("source_file"), str(image_path))
            self.assertEqual(page_data[0].get("extraction_method"), "image_direct")
            self.assertTrue(page_data[0].get("image"))
            self.assertIn("Engineering diagram image:", page_data[0].get("text", ""))

    def test_extract_image_folder_pages_preserves_sorted_file_order(self) -> None:
        subsystem = self._with_production_runtime()

        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = Path(temp_dir) / "b_diagram.png"
            second_path = Path(temp_dir) / "a_diagram.png"
            first_path.write_bytes(base64.b64decode(SAMPLE_PNG_BASE64))
            second_path.write_bytes(base64.b64decode(SAMPLE_PNG_BASE64))

            payload = subsystem.extract_image_folder_pages(temp_dir, use_markitdown=False)
            page_data = payload.get("page_data", [])

            self.assertEqual(payload.get("image_count"), 2)
            self.assertEqual(
                [page.get("source_file") for page in page_data],
                [str(second_path), str(first_path)],
            )
            self.assertEqual([page.get("page_num") for page in page_data], [0, 1])


if __name__ == "__main__":
    unittest.main()