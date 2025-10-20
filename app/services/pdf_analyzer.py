"""
PDF analysis service (business logic).

- PdfAnalyzer validates the PDF magic header and opens the document.
- Inspects pages to decide has_text vs image_count and classifies the PDF (image_only/text_only/mixed).
- Returns typed results (AnalysisReport) for the router to render/return.
"""

import fitz  # PyMuPDF
from fastapi import HTTPException
from .typing import BytesLike
from ..models.schemas import PageInfo, AnalysisReport

PDF_MAGIC = b"%PDF-"

def is_pdf_signature(head: bytes) -> bool:
    return len(head) >= 5 and head[:5] == PDF_MAGIC

class PdfAnalyzer:
    """Encapsulates PDF validation and page-level analysis."""

    def validate_signature(self, head: bytes) -> None:
        if not is_pdf_signature(head):
            raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    def analyze(self, pdf_bytes: BytesLike) -> AnalysisReport:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupt PDF: {e}")

        pages: list[PageInfo] = []
        for i, page in enumerate(doc, start=1):
            raw_text = page.get_text("text").strip()
            has_text = len(raw_text) > 0
            image_count = len(page.get_images(full=True))
            pages.append(
                PageInfo(
                    page=i, 
                    has_text=has_text, 
                    image_count=image_count,
                    text=raw_text if has_text else None,
                    ))

        if all(not p.has_text for p in pages):
            classification = "image_only"
        elif all(p.has_text for p in pages):
            classification = "text_only"
        else:
            classification = "mixed"

        return AnalysisReport(
            num_pages=len(pages),
            pages=pages,
            classification=classification,  # type: ignore[arg-type]
        )
