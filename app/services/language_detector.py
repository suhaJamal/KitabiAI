# app/services/language_detector.py
"""
Language detection service for PDFs.

- Uses Azure Document Intelligence for accurate text extraction (especially for Arabic).
- Detects if a PDF is primarily Arabic or English based on character analysis.
- Falls back to PyMuPDF if Azure is not available.
"""

import re
import logging
from typing import Literal, Optional
import fitz  # PyMuPDF

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from ..core.config import settings


logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detects primary language of a PDF document using Azure-extracted text."""
    
    def __init__(self, arabic_threshold: float = None):
        self.arabic_threshold = arabic_threshold or settings.ARABIC_RATIO_THRESHOLD
        self._azure_client = None
    
    def detect(self, pdf_bytes: bytes) -> tuple[Literal["arabic", "english"], Optional[str]]:
        """
        Analyze PDF text and return language and extracted text.
        
        Args:
            pdf_bytes: Raw PDF file bytes
            
        Returns:
            Tuple of (language, extracted_text)
            - language: 'arabic' if Arabic ratio exceeds threshold, else 'english'
            - extracted_text: Full text from Azure (or None if using PyMuPDF fallback)
        """
        # Try Azure first (better for Arabic)
        if settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and settings.AZURE_DOCUMENT_INTELLIGENCE_KEY:
            try:
                text = self._extract_with_azure(pdf_bytes)
                if text:
                    arabic_ratio = self.get_arabic_ratio(text)
                    language = "arabic" if arabic_ratio > self.arabic_threshold else "english"
                    logger.info(f"Language detected via Azure: {language} (Arabic ratio: {arabic_ratio:.2%})")
                    #title = self.extract_book_title(text, "Unknown")

                    return language, text
            except Exception as e:
                logger.warning(f"Azure extraction failed, falling back to PyMuPDF: {e}")
        
        # Fallback to PyMuPDF
        text = self._extract_with_pymupdf(pdf_bytes)
        arabic_ratio = self.get_arabic_ratio(text)
        language = "arabic" if arabic_ratio > self.arabic_threshold else "english"
        logger.info(f"Language detected via PyMuPDF: {language} (Arabic ratio: {arabic_ratio:.2%})")
        #title = self.extract_book_title(text, "Unknown")
    
        return language, text
    
    def _extract_with_azure(self, pdf_bytes: bytes) -> str:
        """Use Azure Document Intelligence to extract text from PDF."""
        if self._azure_client is None:
            self._azure_client = DocumentIntelligenceClient(
                endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
                credential=AzureKeyCredential(settings.AZURE_DOCUMENT_INTELLIGENCE_KEY)
            )
        
        poller = self._azure_client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=pdf_bytes
        )
        result = poller.result()
        
        all_text = ""
        for page in result.pages:
            for line in page.lines:
                all_text += line.content + "\n"
        
        logger.info(f"Azure extracted {len(all_text)} characters")
        return all_text
    
    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> str:
        """Fallback text extraction using PyMuPDF."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            # Sample first 10 pages or all pages if fewer
            sample_pages = min(10, doc.page_count)
            all_text = ""
            
            for i in range(sample_pages):
                page = doc[i]
                all_text += page.get_text("text")
            
            doc.close()
            logger.info(f"PyMuPDF extracted {len(all_text)} characters")
            return all_text
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return ""
    
    def get_arabic_ratio(self, text: str) -> float:
        """Calculate ratio of Arabic characters in text."""
        arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
        total_chars = max(len(text.strip()), 1)
        return arabic_chars / total_chars
    
    def extract_book_title(self, pdf_bytes, default="Unknown"):
        """
        Extract book title by finding the text with the largest font size.
        
        Args:
            pdf_bytes: PDF file as bytes
            default: Fallback title if extraction fails
        
        Returns:
            str: Extracted title or default value
        """
        try:
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Only check first 3 pages for title
            max_pages = min(3, doc.page_count)
            
            largest_font_size = 0
            title_text = default
            
            for page_num in range(max_pages):
                page = doc[page_num]
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                font_size = span.get("size", 0)
                                text = span.get("text", "").strip()
                                
                                # Update if this is the largest font and has meaningful text
                                if font_size > largest_font_size and len(text) > 3:
                                    largest_font_size = font_size
                                    title_text = text
            
            doc.close()
            
            # Clean up the title
            title_text = title_text.strip()
            
            logger.info(f"Extracted title: '{title_text}' (font size: {largest_font_size})")
            return title_text if title_text else default
            
        except Exception as e:
            logger.warning(f"Failed to extract title by font size: {e}")
            return default