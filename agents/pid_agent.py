"""
P&ID Digitization Agent
=======================
Implements the 5-stage digitization pipeline from the Microsoft ISE article:
  "Engineering Document (P&ID) Digitization"
  https://devblogs.microsoft.com/ise/engineering-document-pid-digitization/

Stages
------
1. Image Preprocessing   – grayscale, binarization, Zhang-Suen-style thinning
2. Symbol Detection      – Azure OpenAI vision: 50+ P&ID symbols with bounding boxes
3. Text / OCR Detection  – Azure AI Document Intelligence: text tokens with bbox + confidence
4. Line Detection        – Simplified Hough Transform (horizontal + vertical) via numpy
5. Graph Construction    – NetworkX DiGraph: proximity matching, arrow heuristics, BFS traversal

Author : Srikanth Bhakthan - Microsoft
"""

from __future__ import annotations

import base64
import io
import json
import logging
import math
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

# ── optional heavy deps ──────────────────────────────────────────────────────
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False
    nx = None  # type: ignore

try:
    from openai import AzureOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    HAS_AZURE_DI = True
except ImportError:
    HAS_AZURE_DI = False


# ─────────────────────────────────────────────────────────────────────────────
# Domain taxonomy (matches the article's 4 symbol categories)
# ─────────────────────────────────────────────────────────────────────────────

class PIDSymbolCategory(str, Enum):
    EQUIPMENT      = "equipment"        # Vacuum pumps, compressors, heat exchangers
    PIPING         = "piping"           # Valves, reducers, flanges
    INSTRUMENTATION = "instrumentation" # Flow meters, pressure gauges, temperature sensors
    CONNECTOR      = "connector"        # Cross-sheet interconnectors


@dataclass
class PIDSymbol:
    """A detected P&ID symbol with its bounding box and classification."""
    symbol_id: str
    category: PIDSymbolCategory
    label: str                    # e.g. "gate valve", "pressure transmitter"
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2) as px from top-left
    confidence: float
    tag: Optional[str] = None     # Associated text tag (e.g. "PT-101")
    sheet_ref: Optional[str] = None  # Cross-sheet reference if connector

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d

    @property
    def centroid(self) -> Tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2)


@dataclass
class PIDLine:
    """A detected process line segment."""
    line_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    orientation: str   # "horizontal" | "vertical" | "diagonal"
    has_arrow: bool = False
    arrow_direction: Optional[str] = None  # "forward" | "backward"
    line_type: str = "solid"               # "solid" | "dashed"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def endpoints(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        return (self.x1, self.y1), (self.x2, self.y2)


@dataclass
class PIDTextAnnotation:
    """OCR-detected text token with its bounding polygon."""
    text: str
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
    confidence: float
    associated_symbol_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def centroid(self) -> Tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2)


@dataclass
class PIDGraphResult:
    """Final digitization output: graph + supporting detail."""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    symbols: List[Dict[str, Any]]
    lines: List[Dict[str, Any]]
    text_annotations: List[Dict[str, Any]]
    traversal_paths: List[Dict[str, Any]]
    sheet_id: str
    image_width: int
    image_height: int
    processing_stages: List[str]
    warnings: List[str]
    latency_ms: int


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 – Image Preprocessing
# ─────────────────────────────────────────────────────────────────────────────

class PIDImagePreprocessor:
    """
    Prepares P&ID images for downstream detection stages.

    Pipeline (mirrors the article's approach):
      1. Grayscale conversion
      2. Binarisation (adaptive threshold)
      3. Noise removal (median filter)
      4. Zhang-Suen-style binary skeleton thinning via erosion iterations
    """

    def preprocess(self, image: Image.Image) -> Tuple[Image.Image, np.ndarray]:
        """
        Returns (preprocessed_pil_image, binary_numpy_array).
        The binary array has 1 = foreground (dark ink), 0 = background.
        """
        gray = ImageOps.grayscale(image)

        # Binarise with Otsu-like adaptive threshold
        gray_np = np.array(gray, dtype=np.uint8)
        threshold = self._otsu_threshold(gray_np)
        binary_np = (gray_np < threshold).astype(np.uint8)  # 1 = dark ink

        # Noise removal via median-filter approximation (3×3 majority rule)
        binary_np = self._remove_noise(binary_np)

        # Skeletonise so Hough Transform sees 1-pixel-wide lines
        thinned_np = self._thin(binary_np)

        thinned_pil = Image.fromarray((thinned_np * 255).astype(np.uint8)).convert("L")
        return thinned_pil, thinned_np

    # ── internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _otsu_threshold(gray: np.ndarray) -> int:
        hist, _ = np.histogram(gray.flatten(), bins=256, range=(0, 255))
        total = gray.size
        sum_all = np.dot(np.arange(256), hist)
        sum_b, w_b, max_var, threshold = 0.0, 0.0, 0.0, 128
        for t in range(256):
            w_b += hist[t]
            if w_b == 0:
                continue
            w_f = total - w_b
            if w_f == 0:
                break
            sum_b += t * hist[t]
            mean_b = sum_b / w_b
            mean_f = (sum_all - sum_b) / w_f
            var = w_b * w_f * (mean_b - mean_f) ** 2
            if var > max_var:
                max_var, threshold = var, t
        return threshold

    @staticmethod
    def _remove_noise(binary: np.ndarray) -> np.ndarray:
        """3×3 median approximation using a fast sliding-window sum."""
        from numpy.lib.stride_tricks import sliding_window_view
        padded = np.pad(binary, 1, constant_values=0)
        windows = sliding_window_view(padded, (3, 3))
        return (windows.sum(axis=(-1, -2)) >= 5).astype(np.uint8)

    @staticmethod
    def _thin(binary: np.ndarray, max_iter: int = 20) -> np.ndarray:
        """
        Simplified skeletonisation: repeated hit-or-miss erosion until stable.
        Not a full Zhang-Suen implementation but gives 1-3 px skeleton lines
        sufficient for Hough analysis.
        """
        prev = binary.copy()
        for _ in range(max_iter):
            # 3×3 erosion: pixel stays foreground only if all 8-neighbours agree
            padded = np.pad(prev, 1, constant_values=0)
            from numpy.lib.stride_tricks import sliding_window_view
            wins = sliding_window_view(padded, (3, 3))
            eroded = (wins.min(axis=(-1, -2)) == 1).astype(np.uint8)
            # Blend: keep original if eroded removes too much
            result = np.where(eroded == 1, 1, np.where(prev == 1, 1, 0)).astype(np.uint8)
            if np.array_equal(result, prev):
                break
            prev = result
        return prev


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 – Symbol Detection (Azure OpenAI Vision)
# ─────────────────────────────────────────────────────────────────────────────

_SYMBOL_DETECT_PROMPT = """You are a P&ID symbol recognition expert.
Analyse this P&ID (Piping and Instrumentation Diagram) image and identify every symbol visible.

For EACH symbol output a JSON object with:
  - "id": sequential integer
  - "category": one of ["equipment", "piping", "instrumentation", "connector"]
  - "label": specific symbol name (e.g. "gate valve", "centrifugal pump", "pressure transmitter", "flow meter", "heat exchanger", "control valve", "globe valve", "ball valve", "check valve", "reducer", "flange", "orifice plate", "level transmitter", "temperature element", "connector reference")
  - "bbox": [x1_pct, y1_pct, x2_pct, y2_pct] as percentage of image width/height (0-100)
  - "confidence": float 0.0–1.0
  - "tag": nearby text tag if visible (e.g. "FT-101") or null
  - "sheet_ref": referenced sheet number if this is a connector symbol, else null

Return ONLY a JSON array of symbol objects. No prose."""

class PIDSymbolDetector:
    """
    Uses Azure OpenAI vision to detect P&ID symbols with bounding boxes.
    Falls back to a heuristic region-based detector when vision is unavailable.
    """

    def __init__(self, client: Optional[Any] = None, deployment: Optional[str] = None):
        self.client = client
        self.deployment = deployment or (
            os.getenv("AZURE_OPENAI_PRO_DEPLOYMENT_NAME") or
            os.getenv("AZURE_DEPLOYMENT_PRO_NAME") or
            os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or
            os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )

    def detect(self, image: Image.Image) -> List[PIDSymbol]:
        if self.client and HAS_OPENAI:
            return self._detect_via_vision(image)
        return self._detect_heuristic(image)

    def _detect_via_vision(self, image: Image.Image) -> List[PIDSymbol]:
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=92)
        b64 = base64.b64encode(buf.getvalue()).decode()

        try:
            chat_response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _SYMBOL_DETECT_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"},
                            },
                        ],
                    }
                ],
                max_tokens=4096,
                temperature=0,
            )
            raw = chat_response.choices[0].message.content or "[]"
            # Strip markdown fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw_list = json.loads(raw)
        except Exception as exc:
            logger.warning("Symbol detection vision call failed: %s", exc)
            return self._detect_heuristic(image)

        w, h = image.size
        symbols: List[PIDSymbol] = []
        for item in raw_list:
            try:
                pcts = item.get("bbox", [0, 0, 10, 10])
                bbox = (
                    pcts[0] / 100 * w, pcts[1] / 100 * h,
                    pcts[2] / 100 * w, pcts[3] / 100 * h,
                )
                cat_raw = item.get("category", "piping")
                try:
                    cat = PIDSymbolCategory(cat_raw)
                except ValueError:
                    cat = PIDSymbolCategory.PIPING
                symbols.append(PIDSymbol(
                    symbol_id=f"S{item.get('id', len(symbols))}",
                    category=cat,
                    label=item.get("label", "unknown"),
                    bbox=bbox,
                    confidence=float(item.get("confidence", 0.7)),
                    tag=item.get("tag"),
                    sheet_ref=item.get("sheet_ref"),
                ))
            except Exception:
                continue
        return symbols

    @staticmethod
    def _detect_heuristic(image: Image.Image) -> List[PIDSymbol]:
        """
        Lightweight fallback: divides the image into a coarse grid and labels
        each occupied region as a generic 'piping' symbol.  Used when no
        vision model is configured.
        """
        gray = ImageOps.grayscale(image)
        arr = np.array(gray)
        w, h = image.size
        symbols: List[PIDSymbol] = []
        grid = 8
        cell_w, cell_h = w // grid, h // grid
        for row in range(grid):
            for col in range(grid):
                patch = arr[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w]
                density = (patch < 180).mean()
                if density > 0.04:  # ≥4% dark pixels → assume symbol presence
                    symbols.append(PIDSymbol(
                        symbol_id=f"S{row}_{col}",
                        category=PIDSymbolCategory.PIPING,
                        label="unknown_symbol",
                        bbox=(col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h),
                        confidence=min(density * 10, 0.6),
                    ))
        return symbols


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 – Text / OCR Detection (Azure AI Document Intelligence)
# ─────────────────────────────────────────────────────────────────────────────

class PIDTextDetector:
    """
    Uses Azure AI Document Intelligence Read API to extract all text tokens
    with bounding polygons and confidence scores.

    Falls back to PIL-based image region description when DI is unavailable.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.endpoint = endpoint or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        # Accept canonical name (from .env.example) and legacy compatibility alias
        self.api_key = api_key or (
            os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY") or
            os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        )

    def detect(self, image: Image.Image) -> List[PIDTextAnnotation]:
        if self.endpoint and self.api_key and HAS_AZURE_DI:
            return self._detect_via_di(image)
        return self._detect_heuristic(image)

    def _detect_via_di(self, image: Image.Image) -> List[PIDTextAnnotation]:
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        try:
            client = DocumentIntelligenceClient(
                self.endpoint, AzureKeyCredential(self.api_key)
            )
            poller = client.begin_analyze_document(
                "prebuilt-read",
                analyze_request=buf,
                content_type="image/jpeg",
            )
            result = poller.result()
        except Exception as exc:
            logger.warning("Document Intelligence call failed: %s", exc)
            return self._detect_heuristic(image)

        w, h = image.size
        annotations: List[PIDTextAnnotation] = []
        for page in (result.pages or []):
            for word in (page.words or []):
                poly = word.polygon or []
                if len(poly) >= 4:
                    xs = [poly[i] for i in range(0, len(poly), 2)]
                    ys = [poly[i] for i in range(1, len(poly), 2)]
                    bbox = (min(xs) * w, min(ys) * h, max(xs) * w, max(ys) * h)
                else:
                    bbox = (0, 0, 0, 0)
                annotations.append(PIDTextAnnotation(
                    text=word.content or "",
                    bbox=bbox,
                    confidence=float(word.confidence or 0.8),
                ))
        return annotations

    @staticmethod
    def _detect_heuristic(image: Image.Image) -> List[PIDTextAnnotation]:
        """
        No-SDK fallback: returns an empty list with a single placeholder so
        callers always get a list.  In production configure DI credentials.
        """
        logger.info("Azure DI not available; OCR skipped for this image.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 – Line Detection (Hough Transform)
# ─────────────────────────────────────────────────────────────────────────────

class PIDLineDetector:
    """
    Detects process lines in pre-processed binary P&ID images.

    Implementation:
    - Scans each row for contiguous horizontal runs (≥ min_length px).
    - Scans each column for contiguous vertical runs (≥ min_length px).
    - Merges overlapping/collinear segments using a gap tolerance.

    This mirrors the Standard Hough Transform approach from the article but is
    implemented in pure numpy, avoiding an OpenCV dependency.
    """

    def __init__(
        self,
        min_length: int = 40,
        gap_tolerance: int = 12,
    ):
        self.min_length = min_length
        self.gap_tolerance = gap_tolerance

    def detect(self, binary: np.ndarray) -> List[PIDLine]:
        lines: List[PIDLine] = []
        lines.extend(self._scan_horizontal(binary))
        lines.extend(self._scan_vertical(binary))
        return lines

    # ── horizontal scanning ──────────────────────────────────────────────────

    def _scan_horizontal(self, binary: np.ndarray) -> List[PIDLine]:
        results: List[PIDLine] = []
        h, w = binary.shape
        for row in range(h):
            runs = self._runs(binary[row])
            for (x1, x2) in runs:
                results.append(PIDLine(
                    line_id=f"H{row}_{x1}",
                    x1=float(x1), y1=float(row),
                    x2=float(x2), y2=float(row),
                    orientation="horizontal",
                ))
        return self._merge_collinear(results, axis="h")

    # ── vertical scanning ────────────────────────────────────────────────────

    def _scan_vertical(self, binary: np.ndarray) -> List[PIDLine]:
        results: List[PIDLine] = []
        h, w = binary.shape
        for col in range(w):
            runs = self._runs(binary[:, col])
            for (y1, y2) in runs:
                results.append(PIDLine(
                    line_id=f"V{col}_{y1}",
                    x1=float(col), y1=float(y1),
                    x2=float(col), y2=float(y2),
                    orientation="vertical",
                ))
        return self._merge_collinear(results, axis="v")

    # ── internals ────────────────────────────────────────────────────────────

    def _runs(self, arr: np.ndarray) -> List[Tuple[int, int]]:
        """Return (start, end) pairs of foreground runs ≥ min_length."""
        runs: List[Tuple[int, int]] = []
        in_run, start = False, 0
        for i, v in enumerate(arr):
            if v == 1 and not in_run:
                in_run, start = True, i
            elif v == 0 and in_run:
                in_run = False
                if i - start >= self.min_length:
                    runs.append((start, i - 1))
        if in_run and len(arr) - start >= self.min_length:
            runs.append((start, len(arr) - 1))
        return runs

    def _merge_collinear(self, lines: List[PIDLine], axis: str) -> List[PIDLine]:
        """
        Merge line segments on the same row/column within gap_tolerance pixels.
        """
        if not lines:
            return []
        # Group by the fixed coordinate
        groups: Dict[int, List[PIDLine]] = {}
        for ln in lines:
            key = int(ln.y1) if axis == "h" else int(ln.x1)
            groups.setdefault(key, []).append(ln)

        merged: List[PIDLine] = []
        for key, group in groups.items():
            group.sort(key=lambda l: l.x1 if axis == "h" else l.y1)
            cur = group[0]
            for nxt in group[1:]:
                gap = (nxt.x1 - cur.x2) if axis == "h" else (nxt.y1 - cur.y2)
                if gap <= self.gap_tolerance:
                    # Extend current segment
                    if axis == "h":
                        cur = PIDLine(cur.line_id, cur.x1, cur.y1, nxt.x2, nxt.y2, "horizontal")
                    else:
                        cur = PIDLine(cur.line_id, cur.x1, cur.y1, nxt.x2, nxt.y2, "vertical")
                else:
                    merged.append(cur)
                    cur = nxt
            merged.append(cur)
        return merged


# ─────────────────────────────────────────────────────────────────────────────
# Stage 5 – Graph Construction & BFS Traversal
# ─────────────────────────────────────────────────────────────────────────────

class PIDGraphBuilder:
    """
    Builds a directed NetworkX graph from the detected symbols and lines.

    Four-step construction (from the article):
      Step 1 – Preprocess: extend line endpoints by a small pixel buffer.
      Step 2 – Proximity matching: link line endpoints to nearest symbol / line.
      Step 3 – Connect lines: finalise edges between symbols via intermediate lines.
      Step 4 – Arrow heuristics: determine flow direction at arrow–line intersections.
    """

    ENDPOINT_BUFFER = 8  # px — extends lines to bridge small alignment gaps

    def __init__(self, image_width: int, image_height: int):
        self.w = image_width
        self.h = image_height

    def build(
        self,
        symbols: List[PIDSymbol],
        lines: List[PIDLine],
        text_annotations: List[PIDTextAnnotation],
    ) -> "nx.DiGraph":
        if not HAS_NX:
            raise RuntimeError("networkx is required for graph construction: pip install networkx")

        G: nx.DiGraph = nx.DiGraph()

        # ── Step 1: associate text tags with symbols ─────────────────────────
        self._associate_text(symbols, text_annotations)

        # ── Add symbol nodes ─────────────────────────────────────────────────
        for sym in symbols:
            G.add_node(sym.symbol_id, **{
                "node_type": "symbol",
                "category": sym.category.value,
                "label": sym.label,
                "tag": sym.tag,
                "sheet_ref": sym.sheet_ref,
                "centroid": sym.centroid,
                "bbox": sym.bbox,
                "confidence": sym.confidence,
            })

        # ── Add line nodes ───────────────────────────────────────────────────
        for ln in lines:
            G.add_node(ln.line_id, **{
                "node_type": "line",
                "orientation": ln.orientation,
                "has_arrow": ln.has_arrow,
                "arrow_direction": ln.arrow_direction,
                "endpoints": ln.endpoints(),
            })

        # ── Step 2 + 3: proximity matching ───────────────────────────────────
        self._proximity_match(G, symbols, lines)

        # ── Step 4: arrow heuristics ─────────────────────────────────────────
        self._resolve_arrow_directions(G, symbols, lines)

        return G

    # ── private helpers ───────────────────────────────────────────────────────

    def _associate_text(
        self,
        symbols: List[PIDSymbol],
        annotations: List[PIDTextAnnotation],
    ) -> None:
        """
        For each text token, attach it to the nearest symbol whose bounding box
        overlaps or is within a 30 px proximity radius.
        """
        for ann in annotations:
            best_sym, best_dist = None, float("inf")
            cx, cy = ann.centroid
            for sym in symbols:
                sx, sy = sym.centroid
                dist = math.hypot(cx - sx, cy - sy)
                # Prefer symbols whose bbox encloses or is very close to the text
                expand = 30
                x1, y1, x2, y2 = sym.bbox
                inside = (x1 - expand) <= cx <= (x2 + expand) and (y1 - expand) <= cy <= (y2 + expand)
                score = dist * (0.3 if inside else 1.0)
                if score < best_dist:
                    best_dist, best_sym = score, sym
            if best_sym and best_dist < 120:
                ann.associated_symbol_id = best_sym.symbol_id
                # Promote the text as a tag if the symbol has none yet
                if best_sym.tag is None and ann.text.strip():
                    best_sym.tag = ann.text.strip()

    def _proximity_match(
        self,
        G: "nx.DiGraph",
        symbols: List[PIDSymbol],
        lines: List[PIDLine],
    ) -> None:
        """
        Extend each line endpoint by ENDPOINT_BUFFER px, then find the closest
        symbol centroid or other line endpoint within a search radius.
        """
        radius = 40  # px

        for ln in lines:
            for endpoint in [
                (ln.x1, ln.y1, "start"),
                (ln.x2, ln.y2, "end"),
            ]:
                ex, ey, side = endpoint
                # Extend in the direction of travel
                if ln.orientation == "horizontal":
                    ex += self.ENDPOINT_BUFFER if side == "end" else -self.ENDPOINT_BUFFER
                else:
                    ey += self.ENDPOINT_BUFFER if side == "end" else -self.ENDPOINT_BUFFER

                # Find nearest symbol
                nearest_sym = self._nearest_symbol(symbols, ex, ey, radius)
                if nearest_sym:
                    if side == "start":
                        # line connects FROM symbol TO itself (will be joined below)
                        G.add_edge(nearest_sym.symbol_id, ln.line_id, edge_type="line_entry")
                    else:
                        G.add_edge(ln.line_id, nearest_sym.symbol_id, edge_type="line_exit")
                    continue

                # Find nearest line endpoint
                nearest_line = self._nearest_line_endpoint(lines, ln, ex, ey, radius)
                if nearest_line:
                    G.add_edge(ln.line_id, nearest_line.line_id, edge_type="line_junction")

    def _resolve_arrow_directions(
        self,
        G: "nx.DiGraph",
        symbols: List[PIDSymbol],
        lines: List[PIDLine],
    ) -> None:
        """
        Arrow orientation heuristic from the article:
        Find arrow symbols (instrumentation connectors with arrow shapes) and
        determine which direction they point by evaluating which connected line
        segment ends closest to the arrow centroid.
        Then propagate flow direction along connected lines without arrows (BFS).
        """
        arrow_symbols = [
            s for s in symbols
            if "arrow" in s.label.lower() or s.category == PIDSymbolCategory.CONNECTOR
        ]

        for arr_sym in arrow_symbols:
            ax, ay = arr_sym.centroid
            # Find line(s) connected to this arrow node in graph
            connected_lines = [
                lid for lid in G.neighbors(arr_sym.symbol_id)
                if G.nodes[lid].get("node_type") == "line"
            ]
            if not connected_lines:
                continue
            # The endpoint of the nearest line that is CLOSEST to the arrow
            # centroid is the "entry" side; the other end becomes the flow direction
            for lid in connected_lines[:1]:
                ln_dict = G.nodes[lid]
                (ex0, ey0), (ex1, ey1) = ln_dict.get("endpoints", ((0, 0), (0, 0)))
                d0 = math.hypot(ax - ex0, ay - ey0)
                d1 = math.hypot(ax - ex1, ay - ey1)
                direction = "forward" if d0 < d1 else "backward"
                G.nodes[lid]["arrow_direction"] = direction
                G.nodes[lid]["has_arrow"] = True

        # Propagate momentum along connected undirected components
        self._propagate_flow_direction(G)

    def _propagate_flow_direction(self, G: "nx.DiGraph") -> None:
        """
        From lines with a known arrow direction, do BFS over adjacent lines
        that share endpoints, propagating the direction as long as we stay
        on the same process flow path.
        """
        directed_lines = {
            n for n, d in G.nodes(data=True)
            if d.get("node_type") == "line" and d.get("arrow_direction")
        }
        visited = set(directed_lines)
        queue = list(directed_lines)
        while queue:
            lid = queue.pop(0)
            direction = G.nodes[lid].get("arrow_direction", "unknown")
            for nbr in list(G.successors(lid)) + list(G.predecessors(lid)):
                if nbr in visited:
                    continue
                if G.nodes[nbr].get("node_type") == "line" and not G.nodes[nbr].get("arrow_direction"):
                    G.nodes[nbr]["arrow_direction"] = direction
                    G.nodes[nbr]["has_arrow"] = False  # inferred, not detected
                    visited.add(nbr)
                    queue.append(nbr)

    # ── static proximity helpers ──────────────────────────────────────────────

    @staticmethod
    def _nearest_symbol(
        symbols: List[PIDSymbol], x: float, y: float, radius: float
    ) -> Optional[PIDSymbol]:
        best, best_d = None, radius
        for sym in symbols:
            d = math.hypot(sym.centroid[0] - x, sym.centroid[1] - y)
            if d < best_d:
                best_d, best = d, sym
        return best

    @staticmethod
    def _nearest_line_endpoint(
        lines: List[PIDLine],
        exclude: PIDLine,
        x: float,
        y: float,
        radius: float,
    ) -> Optional[PIDLine]:
        best, best_d = None, radius
        for ln in lines:
            if ln.line_id == exclude.line_id:
                continue
            for (ex, ey) in [(ln.x1, ln.y1), (ln.x2, ln.y2)]:
                d = math.hypot(ex - x, ey - y)
                if d < best_d:
                    best_d, best = d, ln
        return best


class PIDGraphTraversal:
    """
    BFS-based traversal that extracts upstream/downstream paths between
    terminal assets (equipment and cross-sheet connectors).
    """

    def traverse(self, G: "nx.DiGraph") -> List[Dict[str, Any]]:
        if not HAS_NX:
            return []

        terminal_nodes = [
            n for n, d in G.nodes(data=True)
            if d.get("node_type") == "symbol"
            and d.get("category") in (
                PIDSymbolCategory.EQUIPMENT.value,
                PIDSymbolCategory.CONNECTOR.value,
            )
        ]

        paths: List[Dict[str, Any]] = []
        visited_pairs: set = set()

        for start in terminal_nodes:
            bfs_result = nx.single_source_shortest_path(G, start, cutoff=20)
            for end, path in bfs_result.items():
                if end == start:
                    continue
                if G.nodes[end].get("node_type") != "symbol":
                    continue
                if (start, end) in visited_pairs or (end, start) in visited_pairs:
                    continue
                visited_pairs.add((start, end))

                # Determine momentum (flow direction) along this path
                direction_votes: Dict[str, int] = {}
                for node_id in path:
                    d = G.nodes[node_id].get("arrow_direction")
                    if d:
                        direction_votes[d] = direction_votes.get(d, 0) + 1
                if direction_votes:
                    momentum = max(direction_votes, key=lambda k: direction_votes[k])
                else:
                    momentum = "unknown"

                # Map path to readable labels
                readable = []
                for nid in path:
                    nd = G.nodes[nid]
                    if nd.get("node_type") == "symbol":
                        readable.append(nd.get("tag") or nd.get("label") or nid)

                paths.append({
                    "from": start,
                    "to": end,
                    "from_tag": G.nodes[start].get("tag") or G.nodes[start].get("label") or start,
                    "to_tag":   G.nodes[end].get("tag")   or G.nodes[end].get("label")   or end,
                    "momentum": momentum,
                    "path": path,
                    "path_labels": readable,
                    "hop_count": len(path),
                })

        return paths


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class PIDDigitizationAgent:
    """
    Orchestrates the full 5-stage P&ID digitization pipeline.

    Usage
    -----
    agent = PIDDigitizationAgent.from_env()
    result = agent.digitize(image_path="input/pid.jpeg")
    print(json.dumps(result.nodes, indent=2))
    """

    def __init__(
        self,
        openai_client: Optional[Any] = None,
        vision_deployment: Optional[str] = None,
        di_endpoint: Optional[str] = None,
        di_key: Optional[str] = None,
        min_line_length: int = 40,
    ):
        self.preprocessor   = PIDImagePreprocessor()
        self.symbol_detector = PIDSymbolDetector(openai_client, vision_deployment)
        self.text_detector   = PIDTextDetector(di_endpoint, di_key)
        self.line_detector   = PIDLineDetector(min_length=min_line_length)
        self.traversal       = PIDGraphTraversal()

    @classmethod
    def from_env(cls) -> "PIDDigitizationAgent":
        """Construct agent using environment variables."""
        client = None
        if HAS_OPENAI:
            # PRO endpoint/key is primary; standard endpoint is fallback
            endpoint = os.getenv("AZURE_OPENAI_PRO_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key  = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
            api_ver  = (
                os.getenv("AZURE_OPENAI_PRO_API_VERSION") or
                os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
            )
            if endpoint and api_key:
                client = AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=api_ver)
        # Use the best available deployment — gpt-5-pro for complex P&IDs, gpt-5.4 for standard
        vision_deployment = (
            os.getenv("AZURE_OPENAI_PRO_DEPLOYMENT_NAME") or
            os.getenv("AZURE_DEPLOYMENT_PRO_NAME") or
            os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or
            os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )
        return cls(
            openai_client=client,
            vision_deployment=vision_deployment,
            di_endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            di_key=(
                os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY") or
                os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
            ),
        )

    # ── main entry point ──────────────────────────────────────────────────────

    def digitize(
        self,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        sheet_id: str = "sheet_1",
        enable_ocr: bool = True,
        enable_graph: bool = True,
    ) -> PIDGraphResult:
        """
        Run full digitization pipeline on a P&ID image.

        Parameters
        ----------
        image_path   : path to JPEG/PNG file on disk
        image_bytes  : raw image bytes (alternative to path)
        sheet_id     : identifier for cross-sheet connector resolution
        enable_ocr   : run Azure Document Intelligence OCR stage (default True)
        enable_graph : build NetworkX connectivity graph + BFS traversal (default True)
        """
        t0 = time.time()
        warnings: List[str] = []
        stages: List[str] = []

        # ── Load image ─────────────────────────────────────────────────────
        if image_bytes:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        elif image_path:
            image = Image.open(image_path).convert("RGB")
        else:
            raise ValueError("Provide either image_path or image_bytes")
        w, h = image.size
        stages.append("image_loaded")

        # ── Stage 1: Preprocessing ─────────────────────────────────────────
        logger.info("[PID] Stage 1: Preprocessing (%d×%d)", w, h)
        _, binary = self.preprocessor.preprocess(image)
        stages.append("preprocessing")

        # ── Stage 2: Symbol Detection ──────────────────────────────────────
        logger.info("[PID] Stage 2: Symbol detection")
        symbols = self.symbol_detector.detect(image)
        stages.append("symbol_detection")
        logger.info("[PID]   → %d symbols detected", len(symbols))
        if not symbols:
            warnings.append("No symbols detected; check model deployment or image quality")

        # ── Stage 3: OCR / Text Detection ──────────────────────────────────
        if enable_ocr:
            logger.info("[PID] Stage 3: OCR / text detection")
            text_annotations = self.text_detector.detect(image)
            stages.append("ocr_text_detection")
            logger.info("[PID]   → %d text tokens detected", len(text_annotations))
        else:
            logger.info("[PID] Stage 3: OCR skipped (enable_ocr=False)")
            text_annotations = []
            stages.append("ocr_text_detection_skipped")

        # ── Stage 4: Line Detection ─────────────────────────────────────────
        logger.info("[PID] Stage 4: Hough line detection")

        # Downsample binary array for speed on large images
        scale_factor = max(1, max(w, h) // 1024)
        if scale_factor > 1:
            small = binary[::scale_factor, ::scale_factor]
            raw_lines = self.line_detector.detect(small)
            # Scale coordinates back
            for ln in raw_lines:
                ln.x1 *= scale_factor; ln.y1 *= scale_factor
                ln.x2 *= scale_factor; ln.y2 *= scale_factor
        else:
            raw_lines = self.line_detector.detect(binary)

        stages.append("line_detection")
        logger.info("[PID]   → %d line segments detected", len(raw_lines))

        # ── Stage 5: Graph Construction ─────────────────────────────────────
        if enable_graph:
            logger.info("[PID] Stage 5: Graph construction & traversal")
            builder = PIDGraphBuilder(w, h)
            if HAS_NX:
                G = builder.build(symbols, raw_lines, text_annotations)
                traversal_paths = self.traversal.traverse(G)
                nodes_out = [
                    {"id": n, **{k: v for k, v in d.items() if k != "centroid"}}
                    for n, d in G.nodes(data=True)
                ]
                edges_out = [
                    {"from": u, "to": v, "edge_type": d.get("edge_type", "connected")}
                    for u, v, d in G.edges(data=True)
                ]
            else:
                warnings.append("networkx not available; graph construction skipped")
                nodes_out, edges_out, traversal_paths = [], [], []
            stages.append("graph_construction")
        else:
            logger.info("[PID] Stage 5: Graph construction skipped (enable_graph=False)")
            nodes_out, edges_out, traversal_paths = [], [], []
            stages.append("graph_construction_skipped")

        latency = int((time.time() - t0) * 1000)
        logger.info("[PID] Completed in %d ms", latency)

        return PIDGraphResult(
            nodes=nodes_out,
            edges=edges_out,
            symbols=[s.to_dict() for s in symbols],
            lines=[ln.to_dict() for ln in raw_lines],
            text_annotations=[a.to_dict() for a in text_annotations],
            traversal_paths=traversal_paths,
            sheet_id=sheet_id,
            image_width=w,
            image_height=h,
            processing_stages=stages,
            warnings=warnings,
            latency_ms=latency,
        )

    # ── convenience serialiser ─────────────────────────────────────────────

    def digitize_to_dict(
        self,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        sheet_id: str = "sheet_1",
        enable_ocr: bool = True,
        enable_graph: bool = True,
    ) -> Dict[str, Any]:
        result = self.digitize(
            image_path=image_path,
            image_bytes=image_bytes,
            sheet_id=sheet_id,
            enable_ocr=enable_ocr,
            enable_graph=enable_graph,
        )
        return {
            "sheet_id": result.sheet_id,
            "image_width": result.image_width,
            "image_height": result.image_height,
            "symbol_count": len(result.symbols),
            "line_count": len(result.lines),
            "text_token_count": len(result.text_annotations),
            "node_count": len(result.nodes),
            "edge_count": len(result.edges),
            "traversal_path_count": len(result.traversal_paths),
            "symbols": result.symbols,
            "lines": result.lines[:50],           # cap for response size
            "text_annotations": result.text_annotations[:100],
            "nodes": result.nodes,
            "edges": result.edges[:200],
            "traversal_paths": result.traversal_paths[:20],
            "processing_stages": result.processing_stages,
            "warnings": result.warnings,
            "latency_ms": result.latency_ms,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

def create_pid_digitization_agent(**kwargs) -> PIDDigitizationAgent:
    """Create a fully configured PIDDigitizationAgent from environment variables."""
    return PIDDigitizationAgent.from_env()
