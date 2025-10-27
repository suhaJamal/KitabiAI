#!/usr/bin/env python3
"""
Validation script: Test if PyMuPDF + character-ratio can replace Azure for language detection.

This script compares two approaches:
1. Current: Azure extraction → character ratio → language
2. Proposed: PyMuPDF extraction → character ratio → language

The key question: Can we detect Arabic even when PyMuPDF produces garbled text?
"""

import re
import sys
import logging
import fitz  # PyMuPDF
from pathlib import Path
from typing import Literal

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.language_detector import LanguageDetector
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuickLanguageDetector:
    """
    Lightweight language detector using PyMuPDF + character ratio.
    This is what we want to test as a replacement for Azure-based detection.
    """

    def __init__(self, arabic_threshold: float = 0.3):
        self.arabic_threshold = arabic_threshold

    def detect(self, pdf_bytes: bytes) -> Literal["arabic", "english"]:
        """
        Detect language using PyMuPDF extraction + character ratio.

        Strategy:
        1. Extract sample text from first 5-10 pages with PyMuPDF (fast, free)
        2. Calculate Arabic character ratio
        3. Return language based on threshold

        Even if Arabic text is garbled, the Arabic Unicode characters
        (U+0600-U+06FF) should still be present.
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            sample_pages = min(10, doc.page_count)

            sample_text = ""
            for i in range(sample_pages):
                page = doc[i]
                sample_text += page.get_text("text")

            doc.close()

            arabic_ratio = self.get_arabic_ratio(sample_text)
            language = "arabic" if arabic_ratio > self.arabic_threshold else "english"

            logger.info(f"QuickDetect: {language} (ratio: {arabic_ratio:.2%}, chars: {len(sample_text)})")

            return language

        except Exception as e:
            logger.error(f"Quick detection failed: {e}")
            return "english"  # Safe fallback

    def get_arabic_ratio(self, text: str) -> float:
        """Calculate ratio of Arabic characters (U+0600-U+06FF) in text."""
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
        print(f"   Text extracted: {len(azure_text)} chars")
        print(f"   Arabic ratio: {azure_detector.get_arabic_ratio(azure_text):.2%}")

        # Show sample of extracted text
        sample = azure_text[:200].replace('\n', ' ')
        print(f"   Sample: {sample}...")

    except Exception as e:
        print(f"❌ Azure failed: {e}")
        azure_lang = None
        azure_text = None

    # Method 2: Proposed approach (PyMuPDF + char ratio)
    print("\n[Method 2] Proposed: PyMuPDF + Character Ratio")
    print("-" * 80)

    quick_detector = QuickLanguageDetector(
        arabic_threshold=settings.ARABIC_RATIO_THRESHOLD
    )

    try:
        quick_lang = quick_detector.detect(pdf_bytes)
        print(f"✅ Result: {quick_lang.upper()}")

        # Show what PyMuPDF actually extracts
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pymupdf_text = doc[0].get_text("text") if doc.page_count > 0 else ""
        doc.close()

        print(f"   Text extracted: {len(pymupdf_text)} chars")
        print(f"   Arabic ratio: {quick_detector.get_arabic_ratio(pymupdf_text):.2%}")

        # Show sample of PyMuPDF text
        sample = pymupdf_text[:200].replace('\n', ' ')
        print(f"   Sample: {sample}...")

    except Exception as e:
        print(f"❌ Quick detection failed: {e}")
        quick_lang = None

    # Comparison
    print("\n[Comparison]")
    print("-" * 80)

    if azure_lang and quick_lang:
        if azure_lang == quick_lang:
            print(f"✅ MATCH! Both detected: {azure_lang.upper()}")
            print("   → Quick detection can replace Azure for language detection!")
        else:
            print(f"❌ MISMATCH!")
            print(f"   Azure detected: {azure_lang.upper()}")
            print(f"   Quick detected: {quick_lang.upper()}")
            print("   → Need to investigate further")
    else:
        print("⚠️  Cannot compare - one method failed")

    return {
        'file': Path(pdf_path).name,
        'azure_lang': azure_lang,
        'quick_lang': quick_lang,
        'match': azure_lang == quick_lang if (azure_lang and quick_lang) else None
    }


def main():
    """
    Main validation function.

    Tests language detection on sample PDFs and compares:
    - Azure Document Intelligence (current, expensive)
    - PyMuPDF + character ratio (proposed, free)
    """

    print("\n" + "="*80)
    print("LANGUAGE DETECTION VALIDATION TEST")
    print("="*80)
    print("\nGoal: Prove that PyMuPDF + character-ratio can detect Arabic")
    print("      even when text is garbled, allowing us to skip Azure")
    print("      for language detection (cost savings!).")
    print("\nStrategy:")
    print("  1. For ENGLISH PDFs: Use PyMuPDF for everything (skip Azure)")
    print("  2. For ARABIC PDFs: Use Azure only for text extraction")
    print()

    # Check if Azure is configured
    if not (settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and
            settings.AZURE_DOCUMENT_INTELLIGENCE_KEY):
        print("❌ Azure Document Intelligence not configured!")
        print("   Please set environment variables:")
        print("   - AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        print("   - AZURE_DOCUMENT_INTELLIGENCE_KEY")
        return

    print("✅ Azure configured")
    print(f"   Endpoint: {settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT[:50]}...")
    print(f"   Arabic threshold: {settings.ARABIC_RATIO_THRESHOLD}")

    # Find sample PDFs
    print("\n" + "="*80)
    print("Looking for test PDFs...")
    print("="*80)

    # Look in common locations
    test_dirs = [
        Path("/home/user/KitabiAI/tests/fixtures"),
        Path("/home/user/KitabiAI/outputs"),
        Path("/home/user/KitabiAI"),
    ]

    pdf_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            pdfs = list(test_dir.glob("*.pdf"))
            pdf_files.extend(pdfs)

    if not pdf_files:
        print("\n⚠️  No PDF files found in:")
        for d in test_dirs:
            print(f"   - {d}")
        print("\nPlease provide path to test PDF:")
        print("   python validate_language_detection.py <path-to-pdf>")
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
        print("\n🎉 SUCCESS! PyMuPDF + character-ratio matches Azure 100%")
        print("\n💡 RECOMMENDATION:")
        print("   Proceed with implementation:")
        print("   1. Use PyMuPDF + char-ratio for quick language detection")
        print("   2. Skip Azure for English PDFs (cost savings!)")
        print("   3. Use Azure only for Arabic text extraction")
    elif matches / len(results) >= 0.8:
        print("\n✅ MOSTLY SUCCESSFUL! >80% match rate")
        print("\n💡 RECOMMENDATION:")
        print("   Proceed with caution:")
        print("   - Review mismatch cases")
        print("   - Consider tuning arabic_threshold")
        print("   - Add fallback to Azure if uncertain")
    else:
        print("\n❌ NEEDS WORK! Low match rate")
        print("\n💡 RECOMMENDATION:")
        print("   - Review test results above")
        print("   - Check if PDFs are image-based (need OCR)")
        print("   - Consider alternative detection methods")

    # Detailed results
    print("\nDetailed Results:")
    print("-" * 80)
    for r in results:
        match_symbol = "✅" if r['match'] else "❌" if r['match'] is False else "⚠️ "
        print(f"{match_symbol} {r['file']}: Azure={r['azure_lang']}, Quick={r['quick_lang']}")


if __name__ == "__main__":
    # Allow passing PDF path as argument
    if len(sys.argv) > 1:
        test_pdf(sys.argv[1])
    else:
        main()
