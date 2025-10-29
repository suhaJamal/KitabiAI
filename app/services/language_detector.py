# app/services/language_detector.py
"""
Language detection service for PDFs with FastText optimization.

- Supports two detection strategies:
  1. FastText-based (fast, free): Quick detection using PyMuPDF + FastText
  2. Legacy Azure-based: Full extraction with Azure + character ratio
- Uses Azure Document Intelligence for Arabic text extraction (accurate)
- Uses PyMuPDF for English text extraction (fast & free)
- Feature flags allow easy rollback to legacy behavior
"""

import re
import logging
from typing import Literal, Optional
from pathlib import Path
import fitz  # PyMuPDF

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from ..core.config import settings


logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Detects primary language of a PDF document.

    Supports two strategies:
    1. FastText-based detection (default, cost-optimized)
    2. Legacy Azure-based detection (backward compatibility)
    """

    def __init__(self, arabic_threshold: float = None):
        self.arabic_threshold = arabic_threshold or settings.ARABIC_RATIO_THRESHOLD
        self._azure_client = None
        self._fasttext_model = None  # Lazy load

    def detect(self, pdf_bytes: bytes) -> tuple[Literal["arabic", "english"], Optional[str]]:
        """
        Analyze PDF and return detected language and extracted text.

        Strategy (controlled by USE_FASTTEXT_DETECTION flag):

        If FastText enabled (default):
          1. Quick detection: PyMuPDF sample (first N pages) → FastText → language
          2. Full extraction based on detected language:
             - Arabic → Azure (accurate for Arabic)
             - English → PyMuPDF (fast & free)

        If FastText disabled (legacy):
          1. Azure extraction → character ratio → language
          2. Fallback to PyMuPDF if Azure unavailable

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            Tuple of (language, extracted_text)
            - language: 'arabic' or 'english'
            - extracted_text: Full text from appropriate extraction method
        """
        if settings.USE_FASTTEXT_DETECTION:
            return self._detect_with_fasttext(pdf_bytes)
        else:
            return self._detect_legacy(pdf_bytes)

    def _detect_with_fasttext(self, pdf_bytes: bytes) -> tuple[Literal["arabic", "english"], Optional[str]]:
        """
        FastText-based detection strategy (cost-optimized).

        Phase 1: Quick Language Detection (free, fast)
          - Extract sample text from first N pages with PyMuPDF
          - Use FastText to detect language from sample
          - Confidence threshold determines if we trust the result

        Phase 2: Full Text Extraction (based on detected language)
          - Arabic → Use Azure (accurate, handles RTL/diacritics)
          - English → Use PyMuPDF (fast, free)

        Fallback: If FastText fails or low confidence, fall back to legacy method
        """
        logger.info("Using FastText detection strategy")

        try:
            # Phase 1: Quick detection with FastText
            language, confidence = self._quick_detect_language(pdf_bytes)

            # Check confidence threshold
            if confidence < settings.FASTTEXT_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"FastText confidence too low ({confidence:.2%} < "
                    f"{settings.FASTTEXT_CONFIDENCE_THRESHOLD:.0%}), "
                    f"falling back to legacy detection"
                )
                return self._detect_legacy(pdf_bytes)

            logger.info(
                f"FastText detected: {language.upper()} "
                f"(confidence: {confidence:.2%})"
            )

            # Phase 2: Full text extraction based on detected language
            if language == "arabic":
                # Use Azure for accurate Arabic text extraction
                if settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and settings.AZURE_DOCUMENT_INTELLIGENCE_KEY:
                    try:
                        text = self._extract_with_azure(pdf_bytes)
                        logger.info(f"Used Azure for Arabic text extraction")
                        return "arabic", text
                    except Exception as e:
                        logger.warning(f"Azure extraction failed: {e}, using PyMuPDF")
                        text = self._extract_full_with_pymupdf(pdf_bytes)
                        return "arabic", text
                else:
                    logger.info("Azure not configured, using PyMuPDF for Arabic")
                    text = self._extract_full_with_pymupdf(pdf_bytes)
                    return "arabic", text
            else:
                # Use PyMuPDF for English (fast & free)
                text = self._extract_full_with_pymupdf(pdf_bytes)
                logger.info(f"Used PyMuPDF for English text extraction")
                return "english", text

        except Exception as e:
            logger.error(f"FastText detection failed: {e}, falling back to legacy")
            return self._detect_legacy(pdf_bytes)

    def _quick_detect_language(self, pdf_bytes: bytes) -> tuple[Literal["arabic", "english"], float]:
        """
        Quick language detection using PyMuPDF + FastText.

        Extracts sample text from first N pages and uses FastText model
        to detect language.

        Returns:
            Tuple of (language, confidence)
            - language: 'arabic' or 'english'
            - confidence: 0.0-1.0 (FastText confidence score)
        """
        # Load FastText model (lazy loading)
        if self._fasttext_model is None:
            self._load_fasttext_model()

        # Extract sample text from first N pages
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            sample_pages = min(settings.FASTTEXT_SAMPLE_PAGES, doc.page_count)

            sample_text = ""
            for i in range(sample_pages):
                page = doc[i]
                sample_text += page.get_text("text") + "\n"

            doc.close()

            if not sample_text.strip():
                logger.warning("No text extracted from sample, assuming English")
                return "english", 0.5  # Low confidence

            # Use FastText to detect language
            # Clean text: remove excessive whitespace
            clean_text = " ".join(sample_text.split())
            text_sample = clean_text[:1000]  # Use first 1000 chars

            # FastText prediction
            predictions = self._fasttext_model.predict(text_sample, k=1)
            detected_lang_code = predictions[0][0].replace('__label__', '')
            confidence = float(predictions[1][0])

            # Map FastText codes to our system
            if detected_lang_code == 'ar':
                language = "arabic"
            elif detected_lang_code == 'en':
                language = "english"
            else:
                logger.warning(f"Unexpected language code: {detected_lang_code}, defaulting to English")
                language = "english"
                confidence = 0.5  # Lower confidence for unexpected languages

            logger.info(
                f"FastText quick detection: {language} "
                f"(code: {detected_lang_code}, confidence: {confidence:.2%}, "
                f"sample: {len(sample_text)} chars)"
            )

            return language, confidence

        except Exception as e:
            logger.error(f"Quick detection failed: {e}")
            raise

    def _load_fasttext_model(self):
        """Lazy load FastText model."""
        try:
            import fasttext

            # Suppress FastText warnings
            fasttext.FastText.eprint = lambda x: None

            model_path = Path(settings.FASTTEXT_MODEL_PATH)

            if not model_path.exists():
                raise FileNotFoundError(
                    f"FastText model not found at: {model_path}. "
                    f"Download from: https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
                )

            logger.info(f"Loading FastText model from: {model_path}")
            self._fasttext_model = fasttext.load_model(str(model_path))
            logger.info("✅ FastText model loaded successfully")

        except ImportError:
            raise ImportError(
                "FastText not installed. Install with: pip install fasttext-wheel"
            )
        except Exception as e:
            logger.error(f"Failed to load FastText model: {e}")
            raise

    def _detect_legacy(self, pdf_bytes: bytes) -> tuple[Literal["arabic", "english"], Optional[str]]:
        """
        Legacy detection strategy (Azure-based).

        This is the original behavior:
        1. Try Azure extraction → calculate character ratio → detect language
        2. Fallback to PyMuPDF if Azure unavailable

        Used when:
        - USE_FASTTEXT_DETECTION = False
        - FastText detection fails
        - FastText confidence too low
        """
        logger.info("Using legacy Azure-based detection strategy")

        # Try Azure first (better for Arabic)
        if settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and settings.AZURE_DOCUMENT_INTELLIGENCE_KEY:
            try:
                text = self._extract_with_azure(pdf_bytes)
                if text:
                    arabic_ratio = self.get_arabic_ratio(text)
                    language = "arabic" if arabic_ratio > self.arabic_threshold else "english"
                    logger.info(f"Language detected via Azure: {language} (Arabic ratio: {arabic_ratio:.2%})")
                    return language, text
            except Exception as e:
                logger.warning(f"Azure extraction failed, falling back to PyMuPDF: {e}")

        # Fallback to PyMuPDF
        text = self._extract_with_pymupdf(pdf_bytes)
        arabic_ratio = self.get_arabic_ratio(text)
        language = "arabic" if arabic_ratio > self.arabic_threshold else "english"
        logger.info(f"Language detected via PyMuPDF: {language} (Arabic ratio: {arabic_ratio:.2%})")

        return language, text

    def _extract_with_azure(self, pdf_bytes: bytes) -> str:
        """
        Use Azure Document Intelligence to extract text from PDF.

        Preserves page boundaries by inserting form feed characters (\f) between pages.
        This allows the analyzer to correctly split text back into pages.
        """
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
        for page_num, page in enumerate(result.pages, start=1):
            page_text = ""
            for line in page.lines:
                page_text += line.content + "\n"

            # Add page text
            all_text += page_text

            # Add form feed character between pages (except after last page)
            if page_num < len(result.pages):
                all_text += "\f"  # Form feed: page boundary marker

        logger.info(f"Azure extracted {len(all_text)} characters from {len(result.pages)} pages")
        return all_text

    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> str:
        """
        Extract sample text using PyMuPDF (legacy method for detection).
        Samples first 10 pages only.
        """
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

    def _extract_full_with_pymupdf(self, pdf_bytes: bytes) -> str:
        """
        Extract full text from entire PDF using PyMuPDF.
        Used for English PDFs in FastText strategy.
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            all_text = ""

            for page_num in range(doc.page_count):
                page = doc[page_num]
                all_text += page.get_text("text") + "\n"

            doc.close()
            logger.info(f"PyMuPDF extracted {len(all_text)} characters from {page_num + 1} pages")
            return all_text
        except Exception as e:
            logger.error(f"Full PyMuPDF extraction failed: {e}")
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
