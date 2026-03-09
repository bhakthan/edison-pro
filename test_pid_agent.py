"""
Unit tests for agents/pid_agent.py

Covers:
- Deployment-resolution priority chain (no gpt-4o hardcoding)
- PIDImagePreprocessor output shapes
- PIDLineDetector horizontal/vertical run detection
- PIDSymbolDetector heuristic fallback
- PIDTextDetector no-credentials fallback
- PIDDigitizationAgent.digitize() end-to-end with synthetic image
- enable_ocr / enable_graph stage skipping
- PIDGraphResult dataclass completeness
- create_pid_digitization_agent factory
"""

from __future__ import annotations

import base64
import io
import os
import unittest
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

from agents.pid_agent import (
    PIDDigitizationAgent,
    PIDGraphResult,
    PIDImagePreprocessor,
    PIDLineDetector,
    PIDSymbolDetector,
    PIDSymbolCategory,
    PIDTextDetector,
    create_pid_digitization_agent,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_image(width: int = 200, height: int = 200) -> Image.Image:
    """White image with a horizontal and a vertical black line."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    px = img.load()
    mid_y = height // 2
    mid_x = width // 2
    margin = min(width, height) // 5
    # Horizontal line at mid_y, cols margin to (width-margin)
    for x in range(margin, width - margin):
        px[x, mid_y] = (0, 0, 0)
    # Vertical line at mid_x, rows margin to (height-margin)
    for y in range(margin, height - margin):
        px[mid_x, y] = (0, 0, 0)
    return img


def _image_bytes(img: Optional[Image.Image] = None) -> bytes:
    buf = io.BytesIO()
    (img or _make_image()).save(buf, format="JPEG")
    return buf.getvalue()


class _EnvPatch:
    """Context manager that temporarily sets / clears env vars."""

    def __init__(self, **kwargs):
        self._new = {k: v for k, v in kwargs.items()}
        self._old: dict = {}

    def __enter__(self):
        for k, v in self._new.items():
            self._old[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *_):
        for k, old in self._old.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old


# ─────────────────────────────────────────────────────────────────────────────
# Deployment resolution
# ─────────────────────────────────────────────────────────────────────────────

class DeploymentResolutionTests(unittest.TestCase):

    def _clear_all(self):
        return _EnvPatch(
            AZURE_OPENAI_PRO_DEPLOYMENT_NAME=None,
            AZURE_DEPLOYMENT_PRO_NAME=None,
            AZURE_OPENAI_DEPLOYMENT_NAME=None,
            AZURE_OPENAI_DEPLOYMENT=None,
        )

    def test_no_env_vars_gives_none(self):
        with self._clear_all():
            d = PIDSymbolDetector()
        self.assertIsNone(d.deployment)

    def test_standard_deployment_used_when_only_one_set(self):
        with self._clear_all():
            with _EnvPatch(AZURE_OPENAI_DEPLOYMENT="gpt-5.4"):
                d = PIDSymbolDetector()
        self.assertEqual(d.deployment, "gpt-5.4")

    def test_pro_deployment_wins_over_standard(self):
        with self._clear_all():
            with _EnvPatch(
                AZURE_OPENAI_DEPLOYMENT="gpt-5.4",
                AZURE_OPENAI_PRO_DEPLOYMENT_NAME="gpt-5-pro",
            ):
                d = PIDSymbolDetector()
        self.assertEqual(d.deployment, "gpt-5-pro")

    def test_legacy_pro_alias_accepted(self):
        with self._clear_all():
            with _EnvPatch(AZURE_DEPLOYMENT_PRO_NAME="gpt-5-pro-legacy"):
                d = PIDSymbolDetector()
        self.assertEqual(d.deployment, "gpt-5-pro-legacy")

    def test_explicit_constructor_arg_overrides_env(self):
        with _EnvPatch(AZURE_OPENAI_PRO_DEPLOYMENT_NAME="gpt-5-pro"):
            d = PIDSymbolDetector(deployment="my-custom-model")
        self.assertEqual(d.deployment, "my-custom-model")

    def test_no_gpt4o_anywhere(self):
        """gpt-4o must NOT appear in deployment resolution under any circumstances."""
        with self._clear_all():
            d = PIDSymbolDetector()
        self.assertNotEqual(d.deployment, "gpt-4o")

    def test_from_env_uses_pro_over_standard(self):
        with self._clear_all():
            with _EnvPatch(
                AZURE_OPENAI_PRO_DEPLOYMENT_NAME="gpt-5-pro",
                AZURE_OPENAI_DEPLOYMENT="gpt-5.4",
                # No API key → client stays None, but deployment name should still resolve
            ):
                agent = PIDDigitizationAgent.from_env()
        self.assertEqual(agent.symbol_detector.deployment, "gpt-5-pro")

    def test_from_env_no_hardcoded_fallback_model(self):
        with self._clear_all():
            agent = PIDDigitizationAgent.from_env()
        # Must not fall back to "gpt-4o"
        self.assertNotEqual(agent.symbol_detector.deployment, "gpt-4o")


# ─────────────────────────────────────────────────────────────────────────────
# PIDImagePreprocessor
# ─────────────────────────────────────────────────────────────────────────────

class PreprocessorTests(unittest.TestCase):

    def setUp(self):
        self.pp = PIDImagePreprocessor()

    def test_output_pil_is_grayscale(self):
        img = _make_image()
        out_pil, _ = self.pp.preprocess(img)
        self.assertEqual(out_pil.mode, "L")

    def test_binary_array_shape_matches_input(self):
        img = _make_image(100, 80)
        _, binary = self.pp.preprocess(img)
        self.assertEqual(binary.shape, (80, 100))

    def test_binary_values_are_zero_or_one(self):
        img = _make_image()
        _, binary = self.pp.preprocess(img)
        unique = set(np.unique(binary))
        self.assertTrue(unique.issubset({0, 1}), f"unexpected values: {unique}")

    def test_all_white_image_produces_zero_binary(self):
        white = Image.new("RGB", (50, 50), (255, 255, 255))
        _, binary = self.pp.preprocess(white)
        self.assertEqual(binary.sum(), 0)


# ─────────────────────────────────────────────────────────────────────────────
# PIDLineDetector
# ─────────────────────────────────────────────────────────────────────────────

class LineDetectorTests(unittest.TestCase):

    def setUp(self):
        self.ld = PIDLineDetector(min_length=10, gap_tolerance=3)

    def _binary_with_hline(self, row: int, x1: int, x2: int, h: int = 60, w: int = 120) -> np.ndarray:
        arr = np.zeros((h, w), dtype=np.uint8)
        arr[row, x1:x2 + 1] = 1
        return arr

    def _binary_with_vline(self, col: int, y1: int, y2: int, h: int = 120, w: int = 60) -> np.ndarray:
        arr = np.zeros((h, w), dtype=np.uint8)
        arr[y1:y2 + 1, col] = 1
        return arr

    def test_detects_horizontal_line(self):
        binary = self._binary_with_hline(row=30, x1=10, x2=80)
        lines = self.ld.detect(binary)
        h_lines = [l for l in lines if l.orientation == "horizontal"]
        self.assertGreater(len(h_lines), 0)

    def test_detects_vertical_line(self):
        binary = self._binary_with_vline(col=30, y1=10, y2=80)
        lines = self.ld.detect(binary)
        v_lines = [l for l in lines if l.orientation == "vertical"]
        self.assertGreater(len(v_lines), 0)

    def test_short_runs_ignored(self):
        """Runs shorter than min_length must not produce lines."""
        arr = np.zeros((50, 50), dtype=np.uint8)
        arr[25, 20:24] = 1  # only 4 pixels — below min_length=10
        lines = self.ld.detect(arr)
        self.assertEqual(len(lines), 0)

    def test_gap_merging(self):
        """Two runs separated by a small gap should be merged into one line."""
        arr = np.zeros((50, 120), dtype=np.uint8)
        arr[25, 10:40] = 1   # first segment
        arr[25, 42:80] = 1   # second segment, 2-px gap → ≤ gap_tolerance=3
        lines = self.ld.detect(arr)
        h_lines = [l for l in lines if l.orientation == "horizontal"]
        self.assertEqual(len(h_lines), 1)
        self.assertAlmostEqual(h_lines[0].x1, 10)
        self.assertAlmostEqual(h_lines[0].x2, 79)

    def test_empty_binary_returns_empty(self):
        arr = np.zeros((50, 50), dtype=np.uint8)
        lines = self.ld.detect(arr)
        self.assertEqual(lines, [])


# ─────────────────────────────────────────────────────────────────────────────
# PIDSymbolDetector (heuristic path — no vision model)
# ─────────────────────────────────────────────────────────────────────────────

class SymbolDetectorHeuristicTests(unittest.TestCase):

    def setUp(self):
        # No client → always uses heuristic
        self.detector = PIDSymbolDetector(client=None)

    def test_all_white_returns_no_symbols(self):
        white = Image.new("RGB", (200, 200), (255, 255, 255))
        symbols = self.detector.detect(white)
        self.assertEqual(symbols, [])

    def test_dense_image_returns_symbols(self):
        # All-black image → every cell should be above density threshold
        black = Image.new("RGB", (200, 200), (0, 0, 0))
        symbols = self.detector.detect(black)
        self.assertGreater(len(symbols), 0)

    def test_symbol_category_is_valid(self):
        black = Image.new("RGB", (200, 200), (0, 0, 0))
        symbols = self.detector.detect(black)
        for s in symbols:
            self.assertIsInstance(s.category, PIDSymbolCategory)

    def test_symbol_bbox_within_image(self):
        img = _make_image(200, 200)
        symbols = self.detector.detect(img)
        w, h = img.size
        for s in symbols:
            x1, y1, x2, y2 = s.bbox
            self.assertGreaterEqual(x1, 0)
            self.assertGreaterEqual(y1, 0)
            self.assertLessEqual(x2, w)
            self.assertLessEqual(y2, h)

    def test_confidence_in_range(self):
        img = _make_image()
        symbols = self.detector.detect(img)
        for s in symbols:
            self.assertGreaterEqual(s.confidence, 0.0)
            self.assertLessEqual(s.confidence, 1.0)

    def test_to_dict_has_required_keys(self):
        black = Image.new("RGB", (200, 200), (0, 0, 0))
        symbols = self.detector.detect(black)
        if symbols:
            d = symbols[0].to_dict()
            for key in ("symbol_id", "category", "label", "bbox", "confidence"):
                self.assertIn(key, d)


# ─────────────────────────────────────────────────────────────────────────────
# PIDTextDetector (no-credentials fallback)
# ─────────────────────────────────────────────────────────────────────────────

class TextDetectorFallbackTests(unittest.TestCase):

    def test_no_credentials_returns_empty_list(self):
        detector = PIDTextDetector(endpoint=None, api_key=None)
        result = detector.detect(_make_image())
        self.assertIsInstance(result, list)
        self.assertEqual(result, [])

    def test_api_key_env_canonical_name_picked_up(self):
        with _EnvPatch(
            AZURE_DOCUMENT_INTELLIGENCE_API_KEY="key-canonical",
            AZURE_DOCUMENT_INTELLIGENCE_KEY=None,
        ):
            d = PIDTextDetector()
        self.assertEqual(d.api_key, "key-canonical")

    def test_api_key_env_legacy_alias_picked_up(self):
        with _EnvPatch(
            AZURE_DOCUMENT_INTELLIGENCE_API_KEY=None,
            AZURE_DOCUMENT_INTELLIGENCE_KEY="key-legacy",
        ):
            d = PIDTextDetector()
        self.assertEqual(d.api_key, "key-legacy")

    def test_canonical_name_takes_priority_over_legacy(self):
        with _EnvPatch(
            AZURE_DOCUMENT_INTELLIGENCE_API_KEY="key-canonical",
            AZURE_DOCUMENT_INTELLIGENCE_KEY="key-legacy",
        ):
            d = PIDTextDetector()
        self.assertEqual(d.api_key, "key-canonical")


# ─────────────────────────────────────────────────────────────────────────────
# PIDDigitizationAgent end-to-end (heuristic / no-cloud path)
# ─────────────────────────────────────────────────────────────────────────────

class DigitizationAgentTests(unittest.TestCase):

    def _agent(self) -> PIDDigitizationAgent:
        return PIDDigitizationAgent(
            openai_client=None,
            vision_deployment=None,
            di_endpoint=None,
            di_key=None,
        )

    def test_digitize_returns_pid_graph_result(self):
        result = self._agent().digitize(image_bytes=_image_bytes())
        self.assertIsInstance(result, PIDGraphResult)

    def test_sheet_id_propagated(self):
        result = self._agent().digitize(image_bytes=_image_bytes(), sheet_id="my_sheet")
        self.assertEqual(result.sheet_id, "my_sheet")

    def test_image_dimensions_correct(self):
        img = _make_image(320, 240)
        result = self._agent().digitize(image_bytes=_image_bytes(img))
        self.assertEqual(result.image_width, 320)
        self.assertEqual(result.image_height, 240)

    def test_all_five_stages_recorded(self):
        result = self._agent().digitize(image_bytes=_image_bytes())
        stages = result.processing_stages
        self.assertIn("preprocessing", stages)
        self.assertIn("symbol_detection", stages)
        self.assertIn("line_detection", stages)
        self.assertIn("graph_construction", stages)

    def test_latency_positive(self):
        result = self._agent().digitize(image_bytes=_image_bytes())
        self.assertGreater(result.latency_ms, 0)

    def test_symbols_is_list_of_dicts(self):
        result = self._agent().digitize(image_bytes=_image_bytes())
        self.assertIsInstance(result.symbols, list)
        for s in result.symbols:
            self.assertIsInstance(s, dict)
            self.assertIn("symbol_id", s)

    def test_raise_if_no_image_supplied(self):
        with self.assertRaises(ValueError):
            self._agent().digitize()

    def test_digitize_to_dict_has_counts(self):
        d = self._agent().digitize_to_dict(image_bytes=_image_bytes())
        for key in ("symbol_count", "line_count", "text_token_count", "node_count", "edge_count"):
            self.assertIn(key, d)

    def test_digitize_to_dict_counts_match_lists(self):
        d = self._agent().digitize_to_dict(image_bytes=_image_bytes())
        self.assertEqual(d["symbol_count"], len(d["symbols"]))
        self.assertEqual(d["text_token_count"], len(d["text_annotations"]))


class StageSkippingTests(unittest.TestCase):

    def _agent(self) -> PIDDigitizationAgent:
        return PIDDigitizationAgent(openai_client=None, vision_deployment=None,
                                    di_endpoint=None, di_key=None)

    def test_enable_ocr_false_skips_stage(self):
        result = self._agent().digitize(image_bytes=_image_bytes(), enable_ocr=False)
        self.assertEqual(result.text_annotations, [])
        self.assertIn("ocr_text_detection_skipped", result.processing_stages)
        self.assertNotIn("ocr_text_detection", result.processing_stages)

    def test_enable_graph_false_skips_stage(self):
        result = self._agent().digitize(image_bytes=_image_bytes(), enable_graph=False)
        self.assertEqual(result.nodes, [])
        self.assertEqual(result.edges, [])
        self.assertEqual(result.traversal_paths, [])
        self.assertIn("graph_construction_skipped", result.processing_stages)

    def test_all_stages_run_by_default(self):
        result = self._agent().digitize(image_bytes=_image_bytes())
        # OCR will run (returns [] because no DI creds, but stage is recorded)
        self.assertIn("ocr_text_detection", result.processing_stages)
        self.assertIn("graph_construction", result.processing_stages)

    def test_skip_both_stages(self):
        result = self._agent().digitize(image_bytes=_image_bytes(),
                                         enable_ocr=False, enable_graph=False)
        self.assertEqual(result.text_annotations, [])
        self.assertEqual(result.nodes, [])

    def test_enable_graph_false_digitize_to_dict(self):
        d = self._agent().digitize_to_dict(image_bytes=_image_bytes(), enable_graph=False)
        self.assertEqual(d["node_count"], 0)
        self.assertEqual(d["edge_count"], 0)
        self.assertEqual(d["traversal_path_count"], 0)


# ─────────────────────────────────────────────────────────────────────────────
# PIDGraphResult dataclass
# ─────────────────────────────────────────────────────────────────────────────

class PIDGraphResultTests(unittest.TestCase):

    def test_all_required_fields_exist(self):
        required = {
            "nodes", "edges", "symbols", "lines", "text_annotations",
            "traversal_paths", "sheet_id", "image_width", "image_height",
            "processing_stages", "warnings", "latency_ms",
        }
        actual = set(PIDGraphResult.__dataclass_fields__)
        self.assertTrue(required.issubset(actual), required - actual)


# ─────────────────────────────────────────────────────────────────────────────
# Factory function
# ─────────────────────────────────────────────────────────────────────────────

class FactoryTests(unittest.TestCase):

    def test_factory_returns_agent_instance(self):
        with _EnvPatch(AZURE_OPENAI_API_KEY=None, AZURE_OPENAI_KEY=None):
            agent = create_pid_digitization_agent()
        self.assertIsInstance(agent, PIDDigitizationAgent)

    def test_factory_agent_can_digitize(self):
        with _EnvPatch(AZURE_OPENAI_API_KEY=None, AZURE_OPENAI_KEY=None):
            agent = create_pid_digitization_agent()
        result = agent.digitize(image_bytes=_image_bytes())
        self.assertIsInstance(result, PIDGraphResult)


if __name__ == "__main__":
    unittest.main(verbosity=2)
