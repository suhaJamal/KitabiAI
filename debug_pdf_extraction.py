#!/usr/bin/env python3
"""
Debug script: Analyze what PyMuPDF extracts from Arabic PDFs.

This helps us understand WHY character-ratio detection failed.
"""

import re
import sys
import fitz  # PyMuPDF
from pathlib import Path


def analyze_pdf_extraction(pdf_path: str):
    """Analyze what PyMuPDF actually extracts from a PDF."""

    print("="*80)
    print(f"PDF EXTRACTION ANALYSIS")
    print("="*80)
    print(f"File: {Path(pdf_path).name}\n")

    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    print(f"📄 PDF Info:")
    print(f"   Total pages: {doc.page_count}")
    print(f"   File size: {len(pdf_bytes):,} bytes\n")

    # Check if PDF is image-based or text-based
    print("="*80)
    print("CHECKING IF PDF IS IMAGE-BASED OR TEXT-BASED")
    print("="*80)

    sample_pages = min(5, doc.page_count)
    text_pages = 0
    image_pages = 0

    for i in range(sample_pages):
        page = doc[i]
        text = page.get_text("text").strip()
        images = page.get_images()

        has_text = len(text) > 50  # At least 50 chars
        has_images = len(images) > 0

        if has_text:
            text_pages += 1
            status = "✅ TEXT-BASED"
        else:
            status = "❌ IMAGE-BASED (scanned)"

        if has_images:
            image_pages += 1

        print(f"Page {i+1}: {status}")
        print(f"   Text length: {len(text)} chars")
        print(f"   Images: {len(images)}")

    print(f"\nSummary (first {sample_pages} pages):")
    print(f"   Text-based pages: {text_pages}/{sample_pages}")
    print(f"   Pages with images: {image_pages}/{sample_pages}")

    if text_pages == 0:
        print("\n⚠️  WARNING: This PDF appears to be IMAGE-BASED (scanned)")
        print("   PyMuPDF cannot extract text from images.")
        print("   You MUST use OCR (Azure) for this PDF.\n")
        doc.close()
        return

    # Extract text from first few pages
    print("\n" + "="*80)
    print("EXTRACTING TEXT WITH PYMUPDF")
    print("="*80)

    sample_text = ""
    for i in range(min(10, doc.page_count)):
        page = doc[i]
        sample_text += page.get_text("text") + "\n"

    doc.close()

    print(f"\nExtracted {len(sample_text)} characters from first {min(10, doc.page_count)} pages\n")

    # Analyze extracted text
    print("="*80)
    print("TEXT ANALYSIS")
    print("="*80)

    # Count Arabic characters
    arabic_chars = re.findall(r'[\u0600-\u06FF]', sample_text)
    arabic_count = len(arabic_chars)

    # Count English characters
    english_chars = re.findall(r'[a-zA-Z]', sample_text)
    english_count = len(english_chars)

    # Count digits
    digits = re.findall(r'\d', sample_text)
    digit_count = len(digits)

    # Total printable characters
    total_chars = len(sample_text.strip())

    print(f"\nCharacter Statistics:")
    print(f"   Total characters: {total_chars:,}")
    print(f"   Arabic chars (U+0600-U+06FF): {arabic_count:,} ({arabic_count/max(total_chars,1)*100:.1f}%)")
    print(f"   English chars (a-zA-Z): {english_count:,} ({english_count/max(total_chars,1)*100:.1f}%)")
    print(f"   Digits (0-9): {digit_count:,} ({digit_count/max(total_chars,1)*100:.1f}%)")

    # Calculate Arabic ratio (your current method)
    arabic_ratio = arabic_count / max(total_chars, 1)
    threshold = 0.3  # Your current threshold

    print(f"\n📊 Arabic Ratio: {arabic_ratio:.2%}")
    print(f"   Threshold: {threshold:.0%}")

    if arabic_ratio > threshold:
        print(f"   ✅ DETECTED AS: ARABIC")
    else:
        print(f"   ❌ DETECTED AS: ENGLISH (ratio too low!)")
        print(f"   ⚠️  This is why detection failed!")

    # Show actual extracted text samples
    print("\n" + "="*80)
    print("EXTRACTED TEXT SAMPLES")
    print("="*80)

    print("\n📝 First 500 characters:")
    print("-" * 80)
    print(sample_text[:500])
    print("-" * 80)

    print("\n📝 Lines with Arabic characters:")
    print("-" * 80)
    lines = sample_text.split('\n')
    arabic_lines = [line for line in lines if re.search(r'[\u0600-\u06FF]', line)]

    if arabic_lines:
        for i, line in enumerate(arabic_lines[:10], 1):
            print(f"{i}. {line.strip()}")
    else:
        print("❌ NO ARABIC CHARACTERS FOUND!")
    print("-" * 80)

    # Diagnosis
    print("\n" + "="*80)
    print("DIAGNOSIS")
    print("="*80)

    if arabic_ratio > threshold:
        print("\n✅ SUCCESS: PyMuPDF extracted enough Arabic characters")
        print("   Character-ratio method should work for this PDF.")
    elif arabic_count > 0 and arabic_ratio < threshold:
        print("\n⚠️  PARTIAL FAILURE: Arabic characters found but ratio too low")
        print(f"   Arabic ratio: {arabic_ratio:.2%} < threshold: {threshold:.0%}")
        print("\n   Possible reasons:")
        print("   1. PDF has lots of English/mixed content")
        print("   2. PyMuPDF extracted garbage characters that diluted ratio")
        print("   3. Threshold is too high")
        print("\n   Solutions:")
        print("   - Lower threshold to accept this PDF as Arabic")
        print("   - Use FastText for better language detection")
        print("   - Check first few pages specifically (TOC area)")
    else:
        print("\n❌ COMPLETE FAILURE: No Arabic characters extracted")
        print("\n   Possible reasons:")
        print("   1. PDF is IMAGE-BASED (scanned) - PyMuPDF can't extract text from images")
        print("   2. PDF uses custom fonts/encoding - PyMuPDF can't decode")
        print("   3. PDF text is corrupted or encrypted")
        print("\n   Solutions:")
        print("   - Use Azure Document Intelligence (OCR) for this PDF")
        print("   - FastText won't help either (no text to detect)")
        print("   - This PDF REQUIRES OCR - no way around it")

    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)

    if text_pages == 0:
        print("\n🔴 IMAGE-BASED PDF: Must use Azure OCR")
        print("   Cost optimization: NOT POSSIBLE for this PDF")
        print("   Azure is required for both detection AND extraction")
    elif arabic_ratio > threshold:
        print("\n🟢 TEXT-BASED PDF with good extraction")
        print("   Cost optimization: POSSIBLE")
        print("   Use PyMuPDF + character-ratio for language detection")
        print("   Use Azure only if detected as Arabic (for better extraction)")
    elif arabic_count > 0:
        print("\n🟡 TEXT-BASED PDF with poor extraction")
        print("   Cost optimization: POSSIBLE with FastText")
        print("   Try: PyMuPDF + FastText for language detection")
        print("   Or: Lower character-ratio threshold")
    else:
        print("\n🔴 TEXT-BASED PDF but no Arabic extracted")
        print("   Cost optimization: RISKY")
        print("   PyMuPDF extraction may be unreliable for this PDF")
        print("   Recommend: Keep using Azure for this type of PDF")


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_pdf_extraction.py <path-to-pdf>")
        print("\nExample:")
        print("   python debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    analyze_pdf_extraction(pdf_path)


if __name__ == "__main__":
    main()
