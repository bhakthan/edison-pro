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
    def _with_enabled_subsystem(self) -> RustParallelSubsystem:
        previous_runtime = os.environ.get("EDISON_RUNTIME_PROFILE")
        os.environ["EDISON_RUNTIME_PROFILE"] = "production"
        self.addCleanup(self._restore_runtime, previous_runtime)
        return RustParallelSubsystem()

    def _with_production_runtime(self) -> RustParallelSubsystem:
        subsystem = self._with_enabled_subsystem()
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

    def test_analyze_chunks_extracts_engineering_signals(self) -> None:
        subsystem = self._with_enabled_subsystem()

        chunks = [
            {
                "chunk_id": "chunk_001",
                "content": "Panel MCC-101 operates at 480V and follows IEEE 1584 arc flash guidance.",
                "metadata": {
                    "chunk_id": "chunk_001",
                    "page_numbers": [0],
                    "diagram_type": "electrical",
                    "reference_numbers": ["MCC-101"],
                    "components": ["panel", "breaker"],
                    "source_file": "sheet_a.png",
                },
            },
            {
                "chunk_id": "chunk_002",
                "content": "Pump P-201 discharge pressure is 125 psi per ASME B31.3.",
                "metadata": {
                    "chunk_id": "chunk_002",
                    "page_numbers": [1],
                    "diagram_type": "pid",
                    "reference_numbers": ["P-201"],
                    "components": ["pump"],
                    "source_file": "sheet_b.png",
                },
            },
        ]

        result = subsystem.analyze_chunks(chunks, {})

        self.assertIn(result.get("backend"), {"rust-native", "python-fallback"})
        self.assertTrue(any(item[0] == "480V" for item in result.get("measurement_frequency", [])))
        self.assertTrue(any(item[0] == "125 psi" for item in result.get("measurement_frequency", [])))
        self.assertTrue(any(item[0] == "IEEE 1584" for item in result.get("standard_frequency", [])))
        self.assertTrue(any(item[0] == "ASME B31.3" for item in result.get("standard_frequency", [])))
        self.assertTrue(any(item[0] == "MCC-101" for item in result.get("tag_frequency", [])))
        self.assertTrue(any(item[0] == "P-201" for item in result.get("tag_frequency", [])))

    def test_prepare_query_context_surfaces_engineering_signals(self) -> None:
        subsystem = self._with_enabled_subsystem()

        chunks = [
            {
                "chunk_id": "chunk_001",
                "content": "Panel MCC-101 operates at 480V and follows IEEE 1584 arc flash guidance.",
                "metadata": {
                    "chunk_id": "chunk_001",
                    "page_numbers": [0],
                    "diagram_type": "electrical",
                    "reference_numbers": ["MCC-101"],
                    "components": ["panel", "breaker"],
                    "source_file": "sheet_a.png",
                },
            },
            {
                "chunk_id": "chunk_002",
                "content": "Pump P-201 discharge pressure is 125 psi per ASME B31.3.",
                "metadata": {
                    "chunk_id": "chunk_002",
                    "page_numbers": [1],
                    "diagram_type": "pid",
                    "reference_numbers": ["P-201"],
                    "components": ["pump"],
                    "source_file": "sheet_b.png",
                },
            },
        ]

        insight_summary = subsystem.analyze_chunks(chunks, {})
        query_context = subsystem.prepare_query_context(
            "What does IEEE 1584 require for MCC-101 at 480V?",
            chunks,
            insight_summary,
        )

        self.assertIn(query_context.get("backend"), {"rust-native", "python-fallback"})
        ranked_chunks = query_context.get("ranked_chunks", [])
        self.assertTrue(ranked_chunks)
        self.assertEqual(ranked_chunks[0].get("chunk_id"), "chunk_001")
        self.assertIn("480V", query_context.get("focus_measurements", []))
        self.assertIn("IEEE 1584", query_context.get("focus_standards", []))
        summary_lines = "\n".join(query_context.get("summary_lines", []))
        self.assertIn("measurements", summary_lines.lower())
        self.assertIn("standards", summary_lines.lower())


if __name__ == "__main__":
    unittest.main()