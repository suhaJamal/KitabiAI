# app/services/toc_extractor.py
"""
Unified TOC extractor supporting both English and Arabic PDFs.

Extraction strategy:
1) Use Azure to extract text and detect language (especially important for Arabic)
2) For English: 
   a) Try native PDF bookmarks (preferred)
   b) If insufficient bookmarks, try pattern-based extraction
   c) Fallback to single section
3) For Arabic: Apply pattern-based TOC extraction on Azure-extracted text
4) Fallback: Single 'Document' section spanning all pages
"""

import logging
from typing import List, Tuple, Optional
import fitz
from fastapi import HTTPException

from opentelemetry import trace

from ..models.schemas import SectionInfo, SectionsReport
from ..core.config import settings
from .language_detector import LanguageDetector
from .arabic_toc_extractor import ArabicTocExtractor
from .english_toc_extractor import EnglishTocExtractor


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class TocExtractor:
    def __init__(self) -> None:
        self.language_detector = LanguageDetector()
        self.arabic_extractor = ArabicTocExtractor()
        self.english_extractor = EnglishTocExtractor()
    
    def extract(self, pdf_bytes: bytes) -> SectionsReport:
        """Extract TOC with tracing."""
        
        with tracer.start_as_current_span("toc_extraction") as span:
            # Detect language and extract text
            with tracer.start_as_current_span("language_detection"):
                language, extracted_text, _ = self.language_detector.detect(pdf_bytes)
                span.set_attribute("language", language)
                logger.info(f"Detected language: {language}")
            
            # Open PDF
            with tracer.start_as_current_span("open_pdf"):
                try:
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    num_pages = doc.page_count
                    span.set_attribute("num_pages", num_pages)
                except Exception as e:
                    span.record_exception(e)
                    raise HTTPException(status_code=400, detail=f"Invalid PDF: {e}")
            
            # Extract based on language
            if language == "arabic":
                with tracer.start_as_current_span("extract_arabic_toc"):
                    if extracted_text:
                        report = self.arabic_extractor.extract(extracted_text)
                    else:
                        report = self._fallback_section(num_pages)
            else:
                with tracer.start_as_current_span("extract_english_toc"):
                    # Pass extracted_text to English extraction for pattern-based fallback
                    report = self._extract_english(doc, extracted_text, num_pages)
            
            # Fix page ranges
            report = self._fix_page_ranges(report, num_pages)
            span.set_attribute("sections_extracted", len(report.sections))
            
            doc.close()
            return report
    
    def _extract_english(
        self, 
        doc: fitz.Document, 
        extracted_text: Optional[str], 
        num_pages: int
    ) -> SectionsReport:
        """
        Extract TOC from English PDF using multiple strategies.
        
        Strategy:
        1) Try native PDF bookmarks (preferred)
        2) If insufficient bookmarks and we have extracted text, try pattern-based extraction
        3) Fallback to single section
        """
        # Try bookmarks first
        bookmarks = self._extract_bookmarks(doc)
        if len(bookmarks) >= settings.MIN_BOOKMARKS_OK:
            logger.info(f"Using {len(bookmarks)} native bookmarks for English PDF")
            sections = self._sections_from_bookmarks(bookmarks, num_pages)
            return SectionsReport(bookmarks_found=True, sections=sections)
        
        logger.info(f"Found only {len(bookmarks)} bookmarks (< {settings.MIN_BOOKMARKS_OK}), trying pattern extraction")
        
        # Try pattern-based extraction if we have text
        if extracted_text:
            pattern_report = self.english_extractor.extract(extracted_text, num_pages)
            if len(pattern_report.sections) > 1:  # More than just fallback
                logger.info(f"Pattern-based extraction successful: {len(pattern_report.sections)} sections")
                return pattern_report
        else:
            # Extract text from PDF if not already available
            logger.info("No cached text, extracting from PDF for pattern matching")
            doc_text = ""
            for page in doc:
                doc_text += page.get_text("text") + "\n"
            
            if doc_text.strip():
                pattern_report = self.english_extractor.extract(doc_text, num_pages)
                if len(pattern_report.sections) > 1:
                    logger.info(f"Pattern-based extraction successful: {len(pattern_report.sections)} sections")
                    return pattern_report
        
        # Final fallback
        logger.info("All extraction methods failed, using single section fallback")
        return self._fallback_section(num_pages)
    
    def _extract_bookmarks(self, doc: fitz.Document) -> List[Tuple[int, str, int]]:
        """
        Extract bookmarks from PDF as (level, title, page) tuples.
        """
        try:
            toc = doc.get_toc(simple=True)
        except Exception:
            try:
                toc = doc.get_toc()
            except Exception:
                toc = None
        
        if not toc:
            return []
        
        bookmarks: List[Tuple[int, str, int]] = []
        num_pages = doc.page_count
        
        for item in toc:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                level = int(item[0])
                title = (str(item[1]) or "").strip() or "Untitled"
                page = max(1, min(num_pages, int(item[2])))
                bookmarks.append((level, title, page))
        
        return bookmarks
    
    def _sections_from_bookmarks(
        self,
        bookmarks: List[Tuple[int, str, int]],
        num_pages: int
    ) -> List[SectionInfo]:
        """
        Convert bookmark entries into SectionInfo with inferred page ranges.
        """
        sections: List[SectionInfo] = []
        counters: List[int] = []
        
        for idx, (level, title, page_start) in enumerate(bookmarks):
            # Determine page_end (until next entry at same/higher level)
            page_end = num_pages
            for j in range(idx + 1, len(bookmarks)):
                level_j, _, page_j = bookmarks[j]
                if level_j <= level:
                    page_end = max(page_start, page_j - 1)
                    break
            
            # Hierarchical numbering (e.g., 1, 1.1, 1.2, 2, ...)
            if len(counters) < level:
                counters.extend([0] * (level - len(counters)))
            counters = counters[:level]
            counters[level - 1] += 1
            section_id = ".".join(str(n) for n in counters)
            
            sections.append(
                SectionInfo(
                    section_id=section_id,
                    title=title,
                    level=level,
                    page_start=page_start,
                    page_end=page_end
                )
            )
        
        return sections
    
    def _fix_page_ranges(self, report: SectionsReport, num_pages: int) -> SectionsReport:
        """
        Fix any page_end values that exceed actual page count or are placeholders.
        """
        for section in report.sections:
            if section.page_end > num_pages or section.page_end == 9999:
                section.page_end = num_pages
        return report
    
    def _fallback_section(self, num_pages: int) -> SectionsReport:
        """Return a single fallback section when TOC extraction fails."""
        return SectionsReport(
            bookmarks_found=False,
            sections=[
                SectionInfo(
                    section_id="1",
                    title="Document",
                    level=1,
                    page_start=1,
                    page_end=num_pages
                )
            ]
        )