#!/usr/bin/env python3
"""
Validation script: Test if PyMuPDF + FastText can replace Azure for language detection.

This script compares two approaches:
1. Current: Azure extraction → character ratio → language
2. Proposed: PyMuPDF extraction → FastText → language

The key question: Can FastText detect Arabic even when PyMuPDF produces garbled text?
"""

import re
import sys
import logging
import fitz  # PyMuPDF
from pathlib import Path
from typing import Literal, Optional

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.language_detector import LanguageDetector
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FastTextLanguageDetector:
    """
    Lightweight language detector using PyMuPDF + FastText.
    This is what we want to test as a replacement for Azure-based detection.
    """

    def __init__(self, model_path: str = "lid.176.ftz"):
        """
        Initialize FastText detector.

        Args:
            model_path: Path to FastText language identification model
        """
        self.model_path = model_path
        self._model = None

    def _load_model(self):
        """Lazy load FastText model."""
        if self._model is None:
            try:
                import fasttext
                logger.info(f"Loading FastText model from: {self.model_path}")

                # Suppress FastText warnings
                fasttext.FastText.eprint = lambda x: None

                self._model = fasttext.load_model(self.model_path)
                logger.info("✅ FastText model loaded successfully")
            except ImportError:
                logger.error("❌ FastText not installed. Install with: pip install fasttext-wheel")
                raise
            except Exception as e:
                logger.error(f"❌ Failed to load FastText model: {e}")
                logger.error(f"   Make sure {self.model_path} exists in current directory")
                logger.error(f"   Download from: https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz")
                raise

    def detect(self, pdf_bytes: bytes) -> tuple[Literal["arabic", "english"], Optional[str]]:
        """
        Detect language using PyMuPDF extraction + FastText.

        Strategy:
        1. Extract sample text from first 5-10 pages with PyMuPDF (fast, free)
        2. Use FastText to detect language from the sample
        3. Return language

        Even if Arabic text is garbled by PyMuPDF, FastText should still
        detect it as Arabic based on character patterns.

        Returns:
            Tuple of (language, sample_text)
        """
        self._load_model()

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            sample_pages = min(10, doc.page_count)

            sample_text = ""
            for i in range(sample_pages):
                page = doc[i]
                sample_text += page.get_text("text") + "\n"

            doc.close()

            if not sample_text.strip():
                logger.warning("No text extracted, assuming English")
                return "english", sample_text

            # FastText detection
            # Clean text: remove excessive whitespace and newlines
            clean_text = " ".join(sample_text.split())

            # FastText expects text without newlines for best results
            # Take first 1000 chars for quick detection
            text_sample = clean_text[:1000]

            # Predict language (returns tuple of labels and probabilities)
            predictions = self._model.predict(text_sample, k=1)
            detected_lang = predictions[0][0].replace('__label__', '')
            confidence = predictions[1][0]

            # Map FastText language codes to our system
            # FastText returns 'ar' for Arabic, 'en' for English
            if detected_lang == 'ar':
                language = "arabic"
            elif detected_lang == 'en':
                language = "english"
            else:
                # Fallback for unexpected language codes
                logger.warning(f"Unexpected language: {detected_lang}, defaulting to English")
                language = "english"

            logger.info(
                f"FastText detected: {language.upper()} "
                f"(code: {detected_lang}, confidence: {confidence:.2%}, "
                f"sample_length: {len(sample_text)} chars)"
            )

            return language, sample_text

        except Exception as e:
            logger.error(f"FastText detection failed: {e}")
            return "english", None  # Safe fallback

    def get_arabic_ratio(self, text: str) -> float:
        """Calculate ratio of Arabic characters (for comparison with old method)."""
        arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
        total_chars = max(len(text.strip()), 1)
        return arabic_chars / total_chars


def test_pdf(pdf_path: str):
    """
    Test a single PDF with both methods and compare results.
    """
    print(f"\n{'='*80}")
    print(f"Testing: {Path(pdf_path).name}")
    print(f"{'='*80}")

    # Read PDF
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    # Method 1: Current approach (Azure)
    print("\n[Method 1] Current: Azure Document Intelligence")
    print("-" * 80)

    azure_detector = LanguageDetector()

    try:
        azure_lang, azure_text = azure_detector.detect(pdf_bytes)
        print(f"✅ Result: {azure_lang.upper()}")
        print(f"   Text extracted: {len(azure_text):,} chars")
        print(f"   Arabic ratio: {azure_detector.get_arabic_ratio(azure_text):.2%}")

        # Show sample of extracted text
        sample = azure_text[:200].replace('\n', ' ')
        print(f"   Sample: {sample}...")

    except Exception as e:
        print(f"❌ Azure failed: {e}")
        azure_lang = None
        azure_text = None

    # Method 2: Proposed approach (PyMuPDF + FastText)
    print("\n[Method 2] Proposed: PyMuPDF + FastText")
    print("-" * 80)

    try:
        fasttext_detector = FastTextLanguageDetector()
        fasttext_lang, fasttext_text = fasttext_detector.detect(pdf_bytes)

        print(f"✅ Result: {fasttext_lang.upper()}")

        if fasttext_text:
            print(f"   Text extracted: {len(fasttext_text):,} chars")
            print(f"   Arabic ratio: {fasttext_detector.get_arabic_ratio(fasttext_text):.2%}")

            # Show sample of PyMuPDF text
            sample = fasttext_text[:200].replace('\n', ' ')
            print(f"   Sample: {sample}...")

    except Exception as e:
        print(f"❌ FastText detection failed: {e}")
        fasttext_lang = None
        fasttext_text = None

    # Comparison
    print("\n[Comparison]")
    print("-" * 80)

    if azure_lang and fasttext_lang:
        if azure_lang == fasttext_lang:
            print(f"✅ MATCH! Both detected: {azure_lang.upper()}")
            print("   → FastText can replace Azure for language detection!")

            # Additional comparison
            if azure_text and fasttext_text:
                azure_ratio = azure_detector.get_arabic_ratio(azure_text)
                fasttext_ratio = fasttext_detector.get_arabic_ratio(fasttext_text)
                ratio_diff = abs(azure_ratio - fasttext_ratio)

                print(f"\n   Arabic ratio comparison:")
                print(f"   - Azure:    {azure_ratio:.2%}")
                print(f"   - FastText: {fasttext_ratio:.2%}")
                print(f"   - Difference: {ratio_diff:.2%}")

        else:
            print(f"❌ MISMATCH!")
            print(f"   Azure detected:    {azure_lang.upper()}")
            print(f"   FastText detected: {fasttext_lang.upper()}")
            print("   → Need to investigate further")

            # Show why they differ
            if azure_text and fasttext_text:
                print(f"\n   Azure Arabic ratio:    {azure_detector.get_arabic_ratio(azure_text):.2%}")
                print(f"   PyMuPDF Arabic ratio:  {fasttext_detector.get_arabic_ratio(fasttext_text):.2%}")

    else:
        print("⚠️  Cannot compare - one method failed")

    return {
        'file': Path(pdf_path).name,
        'azure_lang': azure_lang,
        'fasttext_lang': fasttext_lang,
        'match': azure_lang == fasttext_lang if (azure_lang and fasttext_lang) else None
    }


def main():
    """
    Main validation function.

    Tests language detection on sample PDFs and compares:
    - Azure Document Intelligence (current, expensive)
    - PyMuPDF + FastText (proposed, free)
    """

    print("\n" + "="*80)
    print("LANGUAGE DETECTION VALIDATION TEST - FastText Version")
    print("="*80)
    print("\nGoal: Prove that PyMuPDF + FastText can detect Arabic language")
    print("      even when text is garbled, allowing us to skip Azure")
    print("      for language detection (cost savings!).")
    print("\nStrategy:")
    print("  1. For ENGLISH PDFs: Use PyMuPDF for everything (skip Azure)")
    print("  2. For ARABIC PDFs: Use Azure only for text extraction")
    print()

    # Check FastText model
    print("Checking FastText setup...")
    print("-" * 80)

    model_path = "lid.176.ftz"
    if not Path(model_path).exists():
        print(f"❌ FastText model not found: {model_path}")
        print("\n📥 Please download the model:")
        print("   1. Manual: https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz")
        print("   2. PowerShell: Invoke-WebRequest -Uri 'https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz' -OutFile 'lid.176.ftz'")
        print("   3. Python: python download_fasttext_model.py")
        print(f"\n   Save as: {Path(model_path).absolute()}")
        return

    print(f"✅ FastText model found: {model_path} ({Path(model_path).stat().st_size:,} bytes)")

    # Check if Azure is configured
    if not (settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and
            settings.AZURE_DOCUMENT_INTELLIGENCE_KEY):
        print("\n❌ Azure Document Intelligence not configured!")
        print("   Please set environment variables in .env:")
        print("   - AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        print("   - AZURE_DOCUMENT_INTELLIGENCE_KEY")
        return

    print("✅ Azure configured")
    print(f"   Endpoint: {settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT[:50]}...")

    # Find sample PDFs
    print("\n" + "="*80)
    print("Looking for test PDFs...")
    print("="*80)

    # Look in common locations
    test_dirs = [
        Path("tests/fixtures"),
        Path("outputs"),
        Path("."),
    ]

    pdf_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            pdfs = list(test_dir.glob("*.pdf"))
            pdf_files.extend(pdfs)

    if not pdf_files:
        print("\n⚠️  No PDF files found in:")
        for d in test_dirs:
            print(f"   - {d.absolute()}")
        print("\nPlease provide path to test PDF:")
        print("   python validate_language_detection_fasttext.py <path-to-pdf>")
        return

    print(f"\nFound {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files[:10]:  # Show first 10
        print(f"   - {pdf}")

    if len(pdf_files) > 10:
        print(f"   ... and {len(pdf_files) - 10} more")

    # Test each PDF
    print("\n" + "="*80)
    print("RUNNING TESTS")
    print("="*80)

    results = []
    max_tests = min(5, len(pdf_files))  # Test first 5 PDFs

    for pdf in pdf_files[:max_tests]:
        try:
            result = test_pdf(str(pdf))
            results.append(result)
        except Exception as e:
            logger.error(f"Error testing {pdf}: {e}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if not results:
        print("No results to summarize")
        return

    matches = sum(1 for r in results if r['match'] is True)
    mismatches = sum(1 for r in results if r['match'] is False)
    errors = sum(1 for r in results if r['match'] is None)

    print(f"\nTotal PDFs tested: {len(results)}")
    print(f"  ✅ Matches: {matches} ({matches/len(results)*100:.0f}%)")
    print(f"  ❌ Mismatches: {mismatches}")
    print(f"  ⚠️  Errors: {errors}")

    if matches == len(results):
        print("\n🎉 SUCCESS! PyMuPDF + FastText matches Azure 100%")
        print("\n💡 RECOMMENDATION:")
        print("   Proceed with implementation:")
        print("   1. Use PyMuPDF + FastText for quick language detection")
        print("   2. Skip Azure for English PDFs (cost savings!)")
        print("   3. Use Azure only for Arabic text extraction")
    elif matches / len(results) >= 0.8:
        print("\n✅ MOSTLY SUCCESSFUL! >80% match rate")
        print("\n💡 RECOMMENDATION:")
        print("   Proceed with caution:")
        print("   - Review mismatch cases")
        print("   - Add fallback to Azure if FastText uncertain")
    else:
        print("\n❌ NEEDS WORK! Low match rate")
        print("\n💡 RECOMMENDATION:")
        print("   - Review test results above")
        print("   - Check if PDFs are image-based (need OCR)")
        print("   - Consider character-ratio method instead")

    # Detailed results
    print("\nDetailed Results:")
    print("-" * 80)
    for r in results:
        match_symbol = "✅" if r['match'] else "❌" if r['match'] is False else "⚠️ "
        print(f"{match_symbol} {r['file']}: Azure={r['azure_lang']}, FastText={r['fasttext_lang']}")


if __name__ == "__main__":
    # Allow passing PDF path as argument
    if len(sys.argv) > 1:
        test_pdf(sys.argv[1])
    else:
        main()
