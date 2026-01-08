"""
OCR Detector - Detects if PDF is scanned (image-only) and needs OCR.

This fixes the issue where scanned Arabic PDFs are misclassified as English
because PyMuPDF extracts no text from image-only PDFs.

EXACT COPY from arabic-books-engine/detectors/ocr_detector.py
"""

import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class OCRDetector:
    """
    Detects if a PDF requires OCR processing.

    Strategy:
    1. Sample first N pages
    2. Extract text with PyMuPDF
    3. If very little text extracted → likely scanned/image-only
    4. Check image count as additional signal
    """

    def __init__(
        self,
        sample_pages: int = 10,
        min_chars_threshold: int = 50,
        min_words_threshold: int = 10
    ):
        """
        Initialize OCR detector.

        Args:
            sample_pages: Number of pages to sample for detection
            min_chars_threshold: Minimum chars to consider "has text"
            min_words_threshold: Minimum words to consider "has text"
        """
        self.sample_pages = sample_pages
        self.min_chars_threshold = min_chars_threshold
        self.min_words_threshold = min_words_threshold

    def is_scanned(self, pdf_bytes: bytes) -> tuple[bool, dict]:
        """
        Check if PDF is scanned (image-only).

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            Tuple of (is_scanned, metadata)
            - is_scanned: True if PDF appears to be scanned
            - metadata: Dict with detection details (chars, words, images, etc.)
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = doc.page_count
            sample_size = min(self.sample_pages, total_pages)

            total_chars = 0
            total_words = 0
            total_images = 0
            pages_with_text = 0

            for i in range(sample_size):
                page = doc[i]

                # Extract text
                text = page.get_text("text").strip()
                
                # Check if text is gibberish
                if self._is_gibberish(text):
                    # Treat gibberish as no text
                    continue
                
                total_chars += len(text)
                total_words += len(text.split())

                if len(text) > 10:
                    pages_with_text += 1

                # Count images
                images = page.get_images(full=True)
                total_images += len(images)

            doc.close()

            # Calculate metrics
            avg_chars_per_page = total_chars / sample_size if sample_size > 0 else 0
            avg_words_per_page = total_words / sample_size if sample_size > 0 else 0
            text_page_ratio = pages_with_text / sample_size if sample_size > 0 else 0

            # Decision logic
            is_scanned = (
                total_chars < self.min_chars_threshold or
                total_words < self.min_words_threshold or
                text_page_ratio < 0.2  # Less than 20% of pages have text
            )

            metadata = {
                "total_chars": total_chars,
                "total_words": total_words,
                "total_images": total_images,
                "pages_sampled": sample_size,
                "pages_with_text": pages_with_text,
                "avg_chars_per_page": avg_chars_per_page,
                "avg_words_per_page": avg_words_per_page,
                "text_page_ratio": text_page_ratio,
                "decision": "scanned" if is_scanned else "digital"
            }

            logger.info(
                f"OCR Detection: {metadata['decision'].upper()} | "
                f"Chars: {total_chars}, Words: {total_words}, "
                f"Images: {total_images}, Text pages: {pages_with_text}/{sample_size}"
            )

            return is_scanned, metadata

        except Exception as e:
            logger.error(f"OCR detection failed: {e}")
            # Default to not scanned if detection fails
            return False, {"error": str(e)}

    def _is_gibberish(self, text: str) -> bool:
        """
        Detect if extracted text is gibberish/corrupted.
        
        Signs of gibberish:
        - Very high ratio of non-alphabetic characters
        - Very short average word length
        - Low ratio of actual words vs special chars
        """
        if not text or len(text) < 20:
            return False
        
        # Count character types
        alpha_count = sum(c.isalpha() for c in text)
        digit_count = sum(c.isdigit() for c in text)
        space_count = sum(c.isspace() for c in text)
        total_chars = len(text)
        
        # Calculate ratios
        alpha_ratio = alpha_count / total_chars if total_chars > 0 else 0
        
        # Split into words
        words = text.split()
        if not words:
            return True
        
        # Average word length
        avg_word_len = sum(len(w) for w in words) / len(words)
        
        # Gibberish indicators:
        # 1. Very low alphabetic ratio (< 30%)
        # 2. Very short average word length (< 2 chars)
        # 3. OR very long average word length (> 20 chars - no spaces)
        is_gibberish = (
            alpha_ratio < 0.5 or          # Increase to 50% (was 30%)
            avg_word_len < 3 or            # Increase to 3 chars (was 2)
            avg_word_len > 15              # Decrease to 15 chars (was 20)
        )
        
        return is_gibberish

    def needs_azure_ocr(self, pdf_bytes: bytes) -> bool:
        """
        Simplified check - does this PDF need Azure OCR?

        Returns:
            True if PDF is scanned and needs OCR processing
        """
        is_scanned, _ = self.is_scanned(pdf_bytes)
        return is_scanned
