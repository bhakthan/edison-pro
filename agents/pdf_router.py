from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


@dataclass
class PdfRoutingPlan:
    document_type: str
    recommended_primary: str
    recommended_fallback: str
    prefer_markitdown: bool
    prioritize_visual_analysis: bool
    is_protected: bool
    reasons: List[str]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PdfProcessingRouter:
    """Classify PDFs and choose extraction strategy for engineering workflows."""

    def __init__(self, has_markitdown: bool, has_azure_di: bool):
        self.has_markitdown = has_markitdown
        self.has_azure_di = has_azure_di

    def plan(self, pdf_path: str) -> PdfRoutingPlan:
        if fitz is None:
            return PdfRoutingPlan(
                document_type="unknown",
                recommended_primary="pymupdf",
                recommended_fallback="markitdown" if self.has_markitdown else "none",
                prefer_markitdown=False,
                prioritize_visual_analysis=False,
                is_protected=False,
                reasons=["PyMuPDF unavailable; using conservative defaults"],
                metrics={"pdf_path": str(pdf_path), "error": "pymupdf_not_available"},
            )

        doc = None
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            sampled_pages = min(total_pages, 5)

            page_text_counts: List[int] = []
            page_image_counts: List[int] = []

            for page_idx in range(sampled_pages):
                page = doc[page_idx]
                page_text_counts.append(len(page.get_text().strip()))
                page_image_counts.append(len(page.get_images()))

            avg_chars = int(sum(page_text_counts) / sampled_pages) if sampled_pages else 0
            image_heavy_pages = sum(1 for count in page_image_counts if count > 0)
            image_heavy_ratio = (image_heavy_pages / sampled_pages) if sampled_pages else 0.0
            is_protected = bool(getattr(doc, "is_encrypted", False) or getattr(doc, "needs_pass", False))

            reasons: List[str] = []
            if is_protected:
                document_type = "protected"
                reasons.append("PDF reports encryption/password protection")
            elif avg_chars < 80 and image_heavy_ratio >= 0.5:
                document_type = "scanned"
                reasons.append("Low text density and image-heavy sampled pages")
            elif avg_chars < 220:
                document_type = "mixed"
                reasons.append("Moderate text density suggests mixed raster/text content")
            else:
                document_type = "digital_text"
                reasons.append("Sufficient text density for primary text extraction")

            prefer_markitdown = self.has_markitdown and document_type in {"scanned", "mixed"}
            prioritize_visual = document_type in {"scanned", "mixed", "protected"}
            primary = "markitdown" if prefer_markitdown else "pymupdf"
            fallback = "pymupdf" if prefer_markitdown else ("markitdown" if self.has_markitdown else "none")

            if prioritize_visual and self.has_azure_di:
                reasons.append("Visual-priority route can leverage Azure Document Intelligence")

            metrics = {
                "pdf_path": str(Path(pdf_path)),
                "total_pages": total_pages,
                "sampled_pages": sampled_pages,
                "avg_chars_per_sampled_page": avg_chars,
                "image_heavy_ratio": round(image_heavy_ratio, 3),
                "sample_text_counts": page_text_counts,
                "sample_image_counts": page_image_counts,
            }

            return PdfRoutingPlan(
                document_type=document_type,
                recommended_primary=primary,
                recommended_fallback=fallback,
                prefer_markitdown=prefer_markitdown,
                prioritize_visual_analysis=prioritize_visual,
                is_protected=is_protected,
                reasons=reasons,
                metrics=metrics,
            )
        except Exception as exc:
            return PdfRoutingPlan(
                document_type="unknown",
                recommended_primary="pymupdf",
                recommended_fallback="markitdown" if self.has_markitdown else "none",
                prefer_markitdown=False,
                prioritize_visual_analysis=False,
                is_protected=False,
                reasons=[f"Routing fallback due to error: {exc}"],
                metrics={"pdf_path": str(pdf_path), "error": str(exc)},
            )
        finally:
            if doc is not None:
                doc.close()