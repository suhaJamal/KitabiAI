"""
PDF analysis service (business logic).

- PdfAnalyzer validates the PDF magic header and opens the document.
- Inspects pages to decide has_text vs image_count and classifies the PDF (image_only/text_only/mixed).
- Returns typed results (AnalysisReport) for the router to render/return.
- Supports pre-extracted text from Azure for Arabic PDFs to maintain quality.
"""


import fitz  # PyMuPDF
from typing import Optional
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

    def analyze(
        self,
        pdf_bytes: BytesLike,
        extracted_text: Optional[str] = None,
        language: Optional[str] = None
    ) -> AnalysisReport:
        """
        Analyze PDF and extract page information.

        Args:
            pdf_bytes: PDF file content
            extracted_text: Pre-extracted text from Azure (for Arabic PDFs)
            language: Detected language ('arabic' or 'english')

        Returns:
            AnalysisReport with page-level information
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupt PDF: {e}")

        # If we have pre-extracted text from Azure (for Arabic), split it across pages
        page_texts: Optional[list[str]] = None
        if extracted_text and language == "arabic":
            num_pages = len(doc)
            # Try to split by form feed character (page break) or distribute evenly
            if '\f' in extracted_text:
                # Split by form feed (page break character)
                page_texts = extracted_text.split('\f')
                # Ensure we have enough pages
                while len(page_texts) < num_pages:
                    page_texts.append("")
            else:
                # Distribute evenly by character count
                chars_per_page = len(extracted_text) // num_pages if num_pages > 0 else 0
                page_texts = []
                for i in range(num_pages):
                    start = i * chars_per_page
                    end = start + chars_per_page if i < num_pages - 1 else len(extracted_text)
                    page_texts.append(extracted_text[start:end].strip())

        pages: list[PageInfo] = []
        for i, page in enumerate(doc, start=1):
            # Use pre-extracted text for Arabic, PyMuPDF for others
            if page_texts and len(page_texts) >= i:
                raw_text = page_texts[i - 1]
            else:
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
