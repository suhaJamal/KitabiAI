# SR&ED Failed Approaches Documentation
## Record of Unsuccessful Experiments (Critical for SR&ED Claims)

**Project**: KitabiAI - Arabic Book Digitization
**Period**: October 2024 - January 2026

---

## Why Failed Approaches Matter for SR&ED

**CRA SR&ED Guidelines**: "Documentation of failed experiments demonstrates that the work was not routine and faced genuine technological uncertainty."

This document provides evidence that:
1. ✅ We faced real uncertainties (failures prove outcomes weren't predictable)
2. ✅ We conducted systematic investigation (tested multiple hypotheses)
3. ✅ We learned from failures (iterated toward successful solutions)

**Important**: Failed approaches are often MORE valuable for SR&ED claims than successful ones, as they prove technological uncertainty existed.

---

## Failed Approach #1: PyMuPDF-Only Arabic Extraction

**Experiment ID**: EXP-001
**Date**: October 15, 2024
**Duration**: 8 hours (eligible SR&ED time)

### Hypothesis

PyMuPDF (open-source PDF library) can extract Arabic text with >90% accuracy, eliminating the need for expensive Azure OCR services.

**Reasoning Behind Hypothesis**:
- PyMuPDF works well for English text (95%+ accuracy)
- Arabic is standardized Unicode (U+0600 to U+06FF)
- Should be no fundamental difference in PDF text extraction for Arabic vs. English

### Implementation Approach

```python
def extract_text_with_pymupdf(pdf_bytes):
    """Attempt to extract Arabic text using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_text = ""

    for page_num in range(doc.page_count):
        page = doc[page_num]
        all_text += page.get_text("text")  # Default text extraction

    doc.close()
    return all_text
```

**Test Corpus**: 20 Arabic books (12 digital PDFs, 8 scanned PDFs)

### Results

**Accuracy Measurement** (character-level comparison to ground truth):
- Digital PDFs: **78% accuracy** ❌ (target: >90%)
- Scanned PDFs: **42% accuracy** ❌ (target: >90%)
- **Overall: 64% accuracy** (far below target)

**Processing Speed**: ✅ 2.2 seconds/book (very fast)

### Why It Failed

**Root Causes Identified**:

1. **Right-to-Left (RTL) Text Handling**
   - PyMuPDF extracts text in visual rendering order, not logical reading order
   - Example: "السلام عليكم" extracted as "مكيلع مالسلا" (reversed)
   - Impact: ~15% accuracy loss

2. **Diacritics Separated from Base Characters**
   - Arabic diacritics (tashkeel) rendered as separate glyphs
   - Example: "مُحَمَّد" (with diacritics) extracted as "محمد ُ َ َّ" (separated)
   - Impact: ~10% accuracy loss

3. **Font Encoding Issues**
   - Some Arabic PDFs use custom font encodings (not standard Unicode)
   - PyMuPDF maps glyphs to incorrect characters
   - Example: "كتاب" might extract as "‮باتك‬" (garbled)
   - Impact: ~5% accuracy loss

4. **Scanned PDFs Have No Embedded Text**
   - PyMuPDF cannot perform OCR - requires existing text layer
   - Scanned PDFs returned mostly empty text or OCR artifacts
   - Impact: 100% failure for scanned PDFs

### Lessons Learned

**Technical Insights**:
- Arabic text extraction is fundamentally different from English due to RTL rendering
- Free PDF libraries (PyMuPDF, pdfplumber) optimized for LTR languages
- OCR capability essential for scanned documents (not available in PyMuPDF)

**Business Impact**:
- Cost savings from free library (~$0.15/book) not worth 36% accuracy loss
- Would require post-processing to fix RTL issues (complex and error-prone)

### Decision

❌ **ABANDONED** - PyMuPDF-only approach does not meet quality requirements

**Next Step**: Test Azure Document Intelligence as baseline for accuracy.

---

## Failed Approach #2: 70% Confidence Threshold for Routing

**Experiment ID**: EXP-006
**Date**: November 18, 2024
**Duration**: 8 hours (eligible SR&ED time)

### Hypothesis

Industry-standard 70% confidence threshold (used for web text classification) will provide reliable routing decisions for book language detection.

**Reasoning Behind Hypothesis**:
- 70% threshold commonly used in FastText applications
- Published examples show good results at this threshold
- No reason to expect books are different from web text

### Implementation Approach

```python
def route_based_on_language(pdf_bytes):
    """Route to appropriate extraction method based on language."""
    # Detect language with FastText
    text_sample = extract_sample(pdf_bytes, pages=10)
    predictions = fasttext_model.predict(text_sample, k=1)
    language = predictions[0][0].replace('__label__', '')
    confidence = predictions[1][0]

    # Route based on 70% confidence threshold
    if confidence >= 0.70:
        if language == 'ar':
            return extract_with_azure(pdf_bytes)  # Accurate but expensive
        else:
            return extract_with_pymupdf(pdf_bytes)  # Fast and free
    else:
        return extract_with_azure(pdf_bytes)  # Fallback for low confidence
```

**Test Corpus**: 100 books (60 Arabic, 40 English)

### Results

| Confidence Threshold | Books Above | Correct Routes | Wrong Routes | Accuracy | Fallback Rate |
|---------------------|-------------|----------------|--------------|----------|---------------|
| 70% | 98 books | 76 | 22 | **78%** ❌ | 2% |
| 80% | 96 books | 89 | 7 | 93% | 4% |
| **90%** | **92 books** | **87** | **5** | **95%** ✅ | **8%** |

**Critical Finding**: 70% threshold resulted in 22% misrouted books!

### Why It Failed

**Root Causes**:

1. **Book Language Differs from Web Text**
   - FastText model trained on Wikipedia, news articles, social media
   - Books use more formal/literary language
   - Confidence scores systematically lower for books than web text

2. **Mixed-Language Sections**
   - Books contain quotes, references, bibliographies in other languages
   - 10-page sample may include substantial non-primary language text
   - Reduces confidence even when primary language is clear

3. **Technical/Specialized Vocabulary**
   - Academic books contain transliterations, technical terms, proper nouns
   - FastText less certain about non-standard vocabulary
   - Example: Arabic computer science book with English technical terms → 68% confidence (below 70%)

4. **False Positive Rate Too High**
   - 22 out of 98 books misrouted at 70% threshold
   - Impact: Wrong extraction method → poor quality or wasted cost
   - Business impact: ~$4.40 wasted on misrouted books (test corpus)

### Lessons Learned

**Technical Insights**:
- Industry-standard thresholds from web text applications don't transfer to book content
- Domain-specific calibration required for production systems
- Higher threshold (90%) trades coverage for accuracy (acceptable trade-off)

**Business Impact**:
- 70% threshold would have cost $44/1000 books in wasted Azure calls
- 90% threshold costs only $8/1000 books (fewer errors, more fallbacks)

### Decision

❌ **FAILED** - 70% threshold inadequate for book content

✅ **REVISED** - Use 90% confidence threshold

**Rationale**:
- 90% threshold: 95% routing accuracy (meets quality target)
- 8% fallback rate acceptable (ensures quality for ambiguous cases)
- Cost increase minimal (~$0.012/book for fallbacks)

---

## Failed Approach #3: Cover Page Inclusion in Language Sample

**Experiment ID**: EXP-004 (early iteration)
**Date**: November 3, 2024
**Duration**: 4 hours (eligible SR&ED time)

### Hypothesis

Including first 10 pages (starting from page 1) provides best language detection accuracy, as cover and title pages contain representative text.

### Implementation Approach

```python
def extract_sample_including_cover(pdf_bytes):
    """Extract first 10 pages including cover for language detection."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    sample_text = ""

    for i in range(min(10, doc.page_count)):
        page = doc[i]
        sample_text += page.get_text("text")

    return sample_text
```

### Results

| Page Range | Arabic Accuracy | English Accuracy | Overall Accuracy |
|------------|-----------------|------------------|------------------|
| Pages 1-10 (with cover) | **88%** ❌ | 92% | 90% |
| **Pages 4-13 (skip cover)** | **96%** ✅ | 95% | 96% |

**Impact**: Including cover pages reduced accuracy by 6 percentage points!

### Why It Failed

**Root Causes**:

1. **Cover Pages Contain Non-Representative Text**
   - Cover: Title, author, publisher name (often transliterated/mixed language)
   - Copyright page: English legal text even in Arabic books
   - Title page: Decorative text, minimal content
   - Impact: Dilutes language signal from main content

2. **Publisher Information in Multiple Languages**
   - Example: Arabic book published by "Oxford University Press" (English on cover)
   - Bilingual publisher names confuse language detection
   - Impact: 5 Arabic books misclassified as English

3. **Blank Pages and Images**
   - Many books have blank page 1, decorative page 2
   - Reduces text available for classification
   - Lower confidence scores

### Lessons Learned

**Technical Insights**:
- First 3 pages (cover, title, copyright) are not representative of book content
- Skipping front matter improves language detection accuracy
- Main content (pages 4+) provides cleaner signal

### Decision

❌ **FAILED** - Including cover pages reduces accuracy

✅ **REVISED** - Extract pages 4-13 for language detection

**Result**: 96% accuracy (6% improvement over original approach)

---

## Failed Approach #4: 5-Page Sampling for Cost Reduction

**Experiment ID**: EXP-004 (alternative iteration)
**Date**: November 5, 2024
**Duration**: 3 hours (eligible SR&ED time)

### Hypothesis

Reducing sample size from 10 pages to 5 pages will further reduce costs while maintaining >90% language detection accuracy.

**Cost Calculation**:
- 10-page sample: 10 × $0.0015 = $0.015/book
- 5-page sample: 5 × $0.0015 = $0.0075/book
- **Potential 50% cost reduction in sampling phase**

### Implementation Approach

```python
def extract_sample_5_pages(pdf_bytes):
    """Extract only 5 pages (4-8) for language detection."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    sample_text = ""

    for i in range(4, min(9, doc.page_count)):  # Pages 4-8 (5 pages)
        page = doc[i]
        sample_text += page.get_text("text")

    return sample_text
```

### Results

| Sample Size | Accuracy | Cost per Book | Target Met? |
|-------------|----------|---------------|-------------|
| 5 pages | **83%** ❌ | $0.0075 | No (target: >90%) |
| 7 pages | 89% ❌ | $0.0105 | No |
| **10 pages** | **96%** ✅ | **$0.015** | **Yes** |
| 15 pages | 97% ✅ | $0.0225 | Yes (but unnecessary cost) |

**Critical Finding**: 5-page sample fell 7% below accuracy target

### Why It Failed

**Root Causes**:

1. **Insufficient Text for Statistical Reliability**
   - 5 pages: ~2,500-3,000 characters (Arabic books)
   - FastText needs ~5,000+ characters for reliable classification
   - Small sample size → higher variance in predictions

2. **Single Mixed-Language Page Has Outsized Impact**
   - In 5-page sample, one page with English quotes = 20% of sample
   - In 10-page sample, same page = 10% of sample
   - Larger sample dilutes noise from individual pages

3. **Edge Cases More Common in Small Samples**
   - Books that start with English introduction before main Arabic content
   - 5-page sample misses transition to primary language
   - 10-page sample captures both sections, majority wins

### Lessons Learned

**Technical Insights**:
- Minimum viable sample size: ~10 pages for 95%+ accuracy
- Smaller samples increase sensitivity to outlier pages
- Cost savings from smaller sample not worth accuracy loss

**Cost-Benefit Analysis**:
- 5-page approach: Saves $0.0075/book but loses 13% accuracy
- Cost of misclassification: $0.15 (full Azure extraction) + user frustration
- **Expected cost of using 5-page approach**: $0.0075 + (0.17 × $0.15) = $0.033/book
- **Actual cost of 10-page approach**: $0.015/book
- **10-page approach is actually cheaper when accounting for errors!**

### Decision

❌ **FAILED** - 5-page sample does not meet accuracy requirements

✅ **MAINTAINED** - Use 10-page sample (optimal cost-accuracy trade-off)

---

## Failed Approach #5: Text-to-Image Ratio for Scanned PDF Detection

**Experiment ID**: EXP-005 (alternative approach)
**Date**: November 12, 2024
**Duration**: 5 hours (eligible SR&ED time)

### Hypothesis

Using text-to-image ratio (rather than absolute text density) will better distinguish scanned PDFs from digital PDFs.

**Reasoning**:
- Scanned PDFs: High image content (full-page scans), low text
- Digital PDFs: Low image content, high text
- Ratio should be more robust than absolute thresholds

### Implementation Approach

```python
def detect_scanned_by_ratio(pdf_bytes):
    """Detect scanned PDF using text/image ratio."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_text = 0
    total_images = 0

    for page in doc:
        text_length = len(page.get_text("text"))
        image_count = len(page.get_images())

        total_text += text_length
        total_images += image_count

    if total_images == 0:
        return False  # No images → likely digital

    ratio = total_text / total_images
    return ratio < 500  # Threshold TBD
```

### Results

| Approach | Accuracy | False Positives | False Negatives |
|----------|----------|-----------------|-----------------|
| **Text density <100 chars/page** | **95%** ✅ | 3 | 1 |
| Text/image ratio <500 | **87%** ❌ | 8 | 2 |
| Text/image ratio <1000 | 89% ❌ | 6 | 3 |

**Text-to-image ratio performed 8% worse than simple text density!**

### Why It Failed

**Root Causes**:

1. **Digital Books with Many Diagrams**
   - Technical books, textbooks have many images/diagrams
   - High image count → low ratio → misclassified as scanned
   - Example: Computer science textbook with 50 diagrams → false positive

2. **Scanned PDFs Without Images in Metadata**
   - Some scanned PDFs embedded as single background image per page
   - PyMuPDF `get_images()` doesn't detect background images
   - Image count = 0 → ratio calculation fails

3. **Inconsistent Image Detection**
   - Decorative images, logos, figures counted same as full-page scans
   - Small icons have same weight as full-page image in ratio calculation
   - No way to distinguish image types in PyMuPDF

4. **Additional Computational Cost**
   - Extracting image list for all pages adds ~200ms overhead
   - Text density approach only needs text extraction (already done)
   - No accuracy benefit to justify extra computation

### Lessons Learned

**Technical Insights**:
- Simple heuristics often outperform complex ratios
- Text density alone is reliable signal for scanned detection
- Image metadata in PDFs is inconsistent across formats

### Decision

❌ **FAILED** - Text/image ratio less accurate and more complex

✅ **MAINTAINED** - Use text density <100 chars/page (simpler and more accurate)

---

## Failed Approach #6: Single-Pass Language Detection + Extraction

**Experiment ID**: EXP-007 (buggy initial implementation)
**Date**: December 1, 2024
**Duration**: 4 hours debugging (eligible SR&ED time)

### Hypothesis

We can reduce latency by combining language detection and content extraction in a single Azure API call.

**Reasoning**:
- Azure already extracts text during detection phase
- Why make two API calls when one suffices?
- Expected latency reduction: ~30 seconds/book

### Implementation Approach (BUGGY)

```python
def detect_and_extract(pdf_bytes):
    """Detect language AND extract content in single pass."""
    # Extract 10-page sample with Azure
    sample_text, azure_result = extract_with_azure(pdf_bytes, sample_only=True, sample_pages=10)

    # Detect language from sample
    arabic_ratio = get_arabic_ratio(sample_text)
    language = "arabic" if arabic_ratio > 0.3 else "english"

    # BUG: Return sample as if it's full extraction!
    return language, sample_text, azure_result  # ❌ Only 10 pages!
```

### Results

**CRITICAL BUG DISCOVERED**:
- Books only had 10 pages saved to database
- User reported: "Book extracted pages 5-10, no content after page 10"
- 90% of content missing!

**Impact**:
- Deployed to production before testing with long books
- 12 books processed with only 10 pages each
- User unable to generate full book output

### Why It Failed

**Root Cause**:
- Confused sampling phase with extraction phase
- Returned 10-page sample text instead of making second API call for full extraction
- Logic error in phase separation

**What We Missed**:
- Testing with books >10 pages (all test books were short during development)
- Validation that page count matched PDF page count
- End-to-end testing of full workflow

### Lessons Learned

**Technical Insights**:
- Two-phase approach is necessary: sample for detection, then full extraction
- Cannot optimize away second API call without losing content
- Validation checks essential (verify page count = PDF page count)

**Process Insights**:
- Test with realistic data (long books, not just samples)
- Validate outputs match expected dimensions
- Don't optimize prematurely (latency increase of 2 seconds acceptable)

### Decision

❌ **FAILED** - Single-pass approach has critical bug

✅ **FIXED** - Implemented proper two-phase architecture:
1. **Phase 1**: Sample 10 pages for language detection
2. **Phase 2**: Extract ALL pages with appropriate method

**Result**: Bug fixed, full content now extracted correctly

---

## Failed Approach #7: Tesseract OCR as Azure Alternative

**Experiment ID**: Undocumented (brief exploratory test)
**Date**: October 22, 2024
**Duration**: 3 hours (eligible SR&ED time)

### Hypothesis

Tesseract OCR (open-source) could provide comparable accuracy to Azure for Arabic text, reducing costs to zero.

### Implementation Approach

```python
import pytesseract
from PIL import Image

def extract_with_tesseract(pdf_bytes):
    """Extract Arabic text using Tesseract OCR."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_text = ""

    for page in doc:
        # Convert page to image
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # OCR with Arabic language model
        text = pytesseract.image_to_string(img, lang='ara')
        all_text += text

    return all_text
```

### Results

**Test on 5 Arabic books**:
- Average accuracy: **55%** ❌ (target: >90%)
- Processing time: **180 seconds/book** ❌ (very slow)
- Character-level errors: 45%

**Sample Errors**:
- Diacritics completely lost
- Connected letters broken: "سلام" → "س ل ا م"
- Many characters misrecognized: "م" → "ب", "ح" → "خ"

### Why It Failed

**Root Causes**:
1. **Tesseract Arabic model outdated**: Last updated 2017, poor quality
2. **No RTL text handling**: Output in wrong reading order
3. **Very slow**: 3 minutes per book (vs. 45 seconds for Azure)
4. **No table/structure detection**: Plain text only

### Decision

❌ **IMMEDIATELY ABANDONED** - Accuracy far too low (55% vs. 95% target)

**Lesson**: Open-source OCR not viable for production Arabic text extraction

---

## Summary of Failed Approaches

| Failed Approach | Why We Tried It | Why It Failed | Time Invested | Knowledge Gained |
|----------------|-----------------|---------------|---------------|------------------|
| PyMuPDF-only | Cost savings ($0) | RTL issues, 64% accuracy | 8 hours | Free tools inadequate for Arabic |
| 70% confidence threshold | Industry standard | Too low for books, 78% accuracy | 8 hours | Books need higher threshold (90%) |
| Include cover pages | Seemed representative | Front matter not representative | 4 hours | Skip first 3 pages for better accuracy |
| 5-page sampling | Further cost reduction | Insufficient text, 83% accuracy | 3 hours | 10 pages is minimum viable sample |
| Text/image ratio | More sophisticated | Complex, 87% accuracy (vs. 95% for simple density) | 5 hours | Simple heuristics often better |
| Single-pass extraction | Reduce latency | Critical bug, lost 90% of content | 4 hours | Two-phase architecture necessary |
| Tesseract OCR | Zero cost alternative | 55% accuracy, very slow | 3 hours | Open-source Arabic OCR not production-ready |

**Total Time on Failed Approaches**: 35 hours (eligible SR&ED time)

---

## Value of Failed Approaches for SR&ED Claim

### Why These Failures Strengthen the Claim

1. **Proves Technological Uncertainty**
   - If solutions were routine, we wouldn't have had 7 failed approaches
   - Demonstrates outcomes were not predictable in advance

2. **Shows Systematic Investigation**
   - We didn't just try one approach and give up
   - Tested multiple hypotheses, learned from each failure

3. **Generates New Knowledge**
   - Learned that industry-standard thresholds don't apply to books
   - Discovered simple heuristics often outperform complex ratios
   - Identified minimum viable sample size (10 pages)

4. **Demonstrates Iterative Refinement**
   - Each failure led to improved hypothesis
   - Final solution (two-phase with 90% threshold, 10-page sample) informed by all previous failures

### Documentation Provides SR&ED Evidence

- ✅ Detailed record of unsuccessful experiments
- ✅ Root cause analysis for each failure
- ✅ Lessons learned and knowledge generated
- ✅ Time tracking for eligible activities

---

**Conclusion**: Failed approaches are critical evidence of genuine experimental development. They demonstrate that the project faced real technological uncertainties that could not be resolved through routine engineering.

---

**Last Updated**: January 12, 2026
**Maintained By**: [Your name]
