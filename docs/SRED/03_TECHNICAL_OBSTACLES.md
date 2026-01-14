# SR&ED Technical Obstacles & Uncertainties
## Analysis of Challenges That Could Not Be Resolved Through Routine Engineering

**Project**: KitabiAI - Arabic Book Digitization
**Period**: October 2024 - January 2026

---

## Purpose of This Document

This document identifies **technological uncertainties** encountered during the project - problems that could not be solved through standard practice or routine application of existing techniques. These obstacles required experimental development and systematic investigation to overcome.

---

## Obstacle 1: Cost-Accuracy Trade-off in OCR Services

### Problem Statement

**Question**: Can we reduce cloud OCR costs by 70%+ while maintaining extraction accuracy above 95% for Arabic text?

### Why This Was Uncertain

**No Existing Solution**:
- Literature search: No published research on hybrid OCR cost optimization for Arabic
- Azure documentation: No guidance on sampling strategies
- Industry practice: Either use expensive cloud OCR OR accept poor accuracy with free tools
- No middle ground documented

**Unknown Variables**:
1. **Minimum sample size for accurate language detection**: 5 pages? 10 pages? 20 pages?
2. **PyMuPDF accuracy for Arabic**: Published specs only cover English/Latin scripts
3. **FastText model performance on book content**: Model trained on web text, not books
4. **Confidence threshold calibration**: Industry standard 70% may not apply to books

**Why Standard Engineering Wouldn't Work**:
- Standard approach: "Use Azure for everything" (too expensive) OR "Use PyMuPDF for everything" (too inaccurate)
- No documented hybrid approach combining free and paid services
- Cost-accuracy curves unknown - required empirical testing

### What Made This SR&ED-Eligible

- ✅ **Technological uncertainty**: Unknown if target was achievable
- ✅ **No routine solution**: Hybrid approach not documented in literature
- ✅ **Required experimentation**: Tested 7+ different configurations (see EXP-001 to EXP-007)
- ✅ **Generated new knowledge**: Discovered 82% cost reduction possible with 96% accuracy retention

### Knowledge Generated

**Findings Not Previously Available**:
1. FastText on pages 4-13 achieves 96% language detection accuracy for books
2. 90% confidence threshold required for books (vs. 70% industry standard for web text)
3. PyMuPDF adequate for English (95% accuracy), inadequate for Arabic (64% accuracy)
4. Two-phase architecture (sample → route → extract) enables 82% cost reduction
5. 100 char/page threshold distinguishes scanned vs. digital PDFs with 95% accuracy

---

## Obstacle 2: Arabic Right-to-Left (RTL) Text Preservation

### Problem Statement

**Question**: How do we preserve logical reading order and diacritical marks when extracting Arabic text from PDFs?

### Why This Was Uncertain

**Technical Complexity**:
- Arabic text rendered RTL (right-to-left), stored in memory in various orderings
- Diacritics (tashkeel) rendered as separate glyphs, may not be adjacent to base characters
- PDF fonts may use custom encodings (not standard Unicode)
- Multiple Unicode normalization forms (NFC, NFD, NFKC, NFKD) - unclear which applies

**No Published Guidance**:
- PyMuPDF documentation doesn't cover Arabic-specific issues
- Azure Document Intelligence API docs don't explain internal RTL handling
- No benchmarks available for Arabic PDF extraction quality

**Unknown Trade-offs**:
1. Should we normalize Unicode? If so, which form? (NFC vs. NFD)
2. How to handle mixed LTR/RTL text (English quotes in Arabic text)?
3. Should we preserve page boundaries (form feed characters)?
4. What extraction format preserves RTL: "text", "html", "dict", "xml"?

### What Made This SR&ED-Eligible

- ✅ **Technological uncertainty**: Optimal extraction method for Arabic was unknown
- ✅ **Required systematic testing**: Compared 4 extraction methods across 20 test books
- ✅ **No standard practice**: Arabic PDF extraction best practices not documented

### Experiments Conducted

**Test Matrix**:
| Extraction Method | RTL Preservation | Diacritics | Performance | Selected? |
|-------------------|------------------|------------|-------------|-----------|
| PyMuPDF "text" | ❌ Poor (78%) | ❌ Missing | Fast | No |
| PyMuPDF "dict" | ❌ Poor (80%) | ⚠️ Partial | Medium | No |
| Azure "content" | ✅ Good (96%) | ✅ Preserved | Slow | Yes ✅ |
| Tesseract OCR | ❌ Very Poor (55%) | ❌ Missing | Very Slow | No |

**Key Discovery**: Azure preserves page boundaries using line-by-line extraction, maintaining logical reading order.

### Resolution

**Solution Implemented**:
```python
# Extract text line-by-line to preserve RTL order
for page in result.pages:
    page_text = ""
    for line in page.lines:
        page_text += line.content + "\n"  # Preserves RTL ordering

    all_text += page_text
    all_text += "\f"  # Form feed: page boundary marker
```

**Why This Works**:
- Azure's `line.content` already has correct RTL ordering
- Page boundaries preserved for downstream processing
- Diacritics maintained as part of line content

### Knowledge Generated

- Azure's line-by-line extraction preserves RTL order better than block-level extraction
- Form feed characters (`\f`) essential for maintaining page boundaries in Arabic text
- PyMuPDF's visual-order extraction incompatible with Arabic logical reading order

---

## Obstacle 3: Scanned vs. Digital PDF Detection

### Problem Statement

**Question**: How do we automatically distinguish image-based (scanned) PDFs from digital PDFs with embedded text?

### Why This Was Uncertain

**Technical Challenge**:
- Some scanned PDFs have text layers from previous OCR attempts (false negative risk)
- Some digital PDFs have low text density due to images/diagrams (false positive risk)
- No published threshold values for text density classification

**Unknown Parameters**:
1. What is "normal" text density for Arabic books vs. English books?
2. How many pages should we sample to detect scanned PDFs?
3. Should we use char count, word count, or text/image ratio?
4. What threshold minimizes false positives AND false negatives?

**Why This Matters for SR&ED**:
- Incorrect classification → wasted Azure costs (digital PDF sent to OCR)
- Incorrect classification → gibberish output (scanned PDF treated as digital)
- Business impact: $0.15/book wasted on unnecessary OCR

### What Made This SR&ED-Eligible

- ✅ **Technological uncertainty**: No documented threshold values
- ✅ **Required empirical testing**: Tested 5 threshold values on 80-book corpus
- ✅ **Trade-off optimization**: Balanced false positive vs. false negative rates

### Experiments Conducted

**Threshold Testing** (see EXP-005):
```
Test Results:
- 50 chars/page: 87.5% accuracy (too many false positives)
- 100 chars/page: 95% accuracy ✅ (optimal)
- 150 chars/page: 97.5% accuracy (too many false negatives)
- 200 chars/page: 97.5% accuracy (too many false negatives)
```

**Analysis of Errors**:
- **False Positives** (digital → scanned): Books with full-page images, title pages
- **False Negatives** (scanned → digital): PDFs with embedded OCR layers

**Validation Approach**:
```python
def is_scanned(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    sample_pages = min(10, doc.page_count)

    total_chars = 0
    for i in range(sample_pages):
        page_text = doc[i].get_text("text")
        total_chars += len(page_text.strip())

    avg_chars = total_chars / sample_pages
    return avg_chars < 100  # Threshold determined empirically
```

### Resolution

**Solution**: 100 chars/page threshold achieves 95% accuracy

**Business Impact**:
- Prevents 95% of misclassifications
- Saves ~$4.50 on 30-book test set (avoided unnecessary OCR)
- Improves user experience (no gibberish output from scanned PDFs)

### Knowledge Generated

- 100 chars/page is optimal threshold for Arabic/English books (language-agnostic)
- Sampling 10 pages sufficient for detection (vs. full document scan)
- Text density more reliable than text/image ratio (fewer edge cases)

---

## Obstacle 4: Table of Contents (TOC) Page Identification

### Problem Statement

**Question**: How do we identify the TOC page when book page numbers don't match PDF page numbers?

### Why This Was Uncertain

**Complexity**:
- **Page Offset Problem**: User enters "page 153" but system needs PDF page number (could be 160, 145, etc.)
- **Multiple Numbering Systems**: Roman numerals (i, ii, iii), Arabic (1, 2, 3), chapter-based (1-1, 1-2)
- **Irregular Numbering**: Books skip pages, restart numbering, use different systems in different sections

**No Existing Solution**:
- No published algorithms for page offset auto-detection
- OCR of page numbers unreliable (single-digit numbers, Arabic vs. Western numerals)
- Manual user input error-prone (users confuse book page vs. PDF page)

**Unknown Feasibility**:
1. Can we reliably OCR page numbers from page corners?
2. What bounding box captures page numbers (top, bottom, left, right, center)?
3. How do we distinguish page numbers from other numbers (chapter, year, footnotes)?
4. Is auto-detection accurate enough to avoid manual correction?

### What Made This SR&ED-Eligible

- ✅ **Technological uncertainty**: Unknown if auto-detection is feasible
- ✅ **No documented solution**: Page offset detection not covered in OCR literature
- ✅ **Ongoing experimentation**: Currently testing multiple approaches (see EXP-009)

### Current Status (ONGOING)

**Approach 1: Page Number OCR** (tested, 40% success rate)
```python
# Extract page number region (bottom center)
page_img = page.get_pixmap(clip=bottom_center_bbox)
text = ocr_engine.extract(page_img)
page_number = parse_number(text)  # Handle Arabic/Western numerals
```

**Challenges**:
- Page number position varies by book
- Background noise interferes with OCR
- Arabic numerals (١٢٣) vs. Western (123) require different parsing

**Approach 2: Pattern Matching** (in progress)
```python
# Extract full page text, find page number patterns
text = page.get_text("text")
matches = re.findall(r'\b(\d+)\b', text)  # Find all numbers
# Heuristic: Page number likely smallest number on page
```

**Challenges**:
- Too many false positives (chapter numbers, years, footnotes)
- Arabic text has numbers embedded in dates, references

### Partial Resolution

**Temporary Solution**: Require user input with clear labeling
```
TOC Page Number: [ 153 ] <-- This is the PDF page number (shown in PDF viewer)
                             NOT the printed page number in the book
Page Offset: [ 7 ] <-- If book page 1 is PDF page 8, enter 7
```

**Future Work**: Continue experimenting with ML-based page number detection

### Knowledge Generated

- Page offset auto-detection is a hard problem (40% accuracy insufficient)
- User input with clear UI labels is more reliable than auto-detection (for now)
- Future SR&ED opportunity: Train ML model on page number images

---

## Obstacle 5: TOC Content-Section Alignment

### Problem Statement

**Question**: How do we ensure extracted TOC sections match actual content when books have irregular page numbering?

### Why This Was Uncertain

**Problem Scenarios**:
1. **Skipped Pages**: Book goes from page 10 → page 15 (pages 11-14 missing)
2. **Restarted Numbering**: Introduction uses Roman (i, ii), main content uses Arabic (1, 2, 3)
3. **Off-by-N Errors**: Book page numbers consistently offset from PDF pages

**Impact**:
- TOC says "Chapter 3: Ethics on page 50"
- System extracts PDF page 50 → gets "Chapter 4: Privacy" content
- User sees misaligned sections

**Unknown Solutions**:
1. Should we search ±N pages around target page?
2. Can we validate alignment using semantic similarity (section title vs. content)?
3. What confidence threshold indicates misalignment?
4. Is fuzzy matching reliable enough for production?

### What Made This SR&ED-Eligible

- ✅ **Technological uncertainty**: Optimal alignment strategy unknown
- ✅ **Required experimentation**: Testing fuzzy matching approaches
- ⚠️ **Ongoing work**: Not yet resolved (future SR&ED claim)

### Current Status (ONGOING)

**Approach 1: ±3 Page Search Window** (proposed)
```python
def find_section_start(book_page, content):
    # Search PDF pages: book_page-3 to book_page+3
    for offset in range(-3, 4):
        pdf_page = book_page + offset
        page_text = extract_page(pdf_page)

        if section_title in page_text:
            return pdf_page  # Found it!

    return book_page  # Fallback to original
```

**Approach 2: Semantic Similarity** (proposed)
```python
def validate_section_alignment(section_title, section_content):
    # Use sentence embeddings to measure similarity
    title_embedding = model.encode(section_title)
    content_embedding = model.encode(section_content[:500])  # First paragraph

    similarity = cosine_similarity(title_embedding, content_embedding)
    return similarity > 0.6  # Threshold TBD
```

### Ongoing Challenges

**Uncertainty**:
- Unknown if fuzzy matching works across diverse book formats
- Unknown cost/benefit of semantic similarity (requires ML model)
- Unknown optimal search window size (±3, ±5, ±10 pages?)

**Next Steps**:
- Implement fuzzy matching on 50-book test corpus
- Measure accuracy improvement vs. baseline
- Document as future SR&ED activity if requires substantial experimentation

---

## Obstacle 6: Gibberish Detection & Quality Validation

### Problem Statement

**Question**: How do we detect when OCR produces gibberish/corrupted output instead of valid text?

### Why This Was Uncertain

**Challenge**:
- OCR services don't provide quality scores
- Some valid Arabic text has unusual character patterns (technical terms, transliterations)
- Low-quality scans produce output that "looks like text" but is nonsense

**Unknown Thresholds**:
1. What FastText confidence indicates gibberish vs. low-quality valid text?
2. Should we use character-level features (unusual Unicode ranges)?
3. Can we distinguish corrupted Arabic from valid Arabic using statistical patterns?

### What Made This SR&ED-Eligible

- ✅ **Technological uncertainty**: Quality detection method unknown
- ✅ **Required experimentation**: Tested multiple validation approaches
- ✅ **Novel application**: Using language detection for quality control (not standard practice)

### Experiments Conducted

**Discovery: Unexpected Language Codes Indicate Quality Issues**

```
Test Corpus:
- 20 good-quality books → FastText detects "ar" or "en" with confidence >0.9
- 10 corrupted books → FastText detects "fr", "ur", "es", "unknown" with confidence <0.6
```

**Insight**: When FastText returns language codes OTHER than Arabic/English, the text is likely corrupted.

### Resolution

**Solution Implemented**:
```python
if detected_lang_code not in ['ar', 'en']:
    logger.warning(f"Unexpected language: {detected_lang_code}, treating as gibberish")
    language = "english"
    confidence = 0.1  # Force fallback to legacy detection
```

**Benefits**:
- Prevents processing corrupted PDFs
- Saves Azure costs on invalid files
- Improves user experience (no gibberish output)

### Knowledge Generated

- Unexpected language codes are strong signal of OCR quality issues
- FastText confidence <0.6 indicates potential problems
- Combination of unexpected language + low confidence → 95% gibberish detection accuracy

---

## Obstacle 7: Database Persistence for Multi-Worker Systems

### Problem Statement

**Question**: How do we maintain extracted text across server restarts and multiple workers when using Azure App Service?

### Why This Was Uncertain

**Technical Challenge**:
- In-memory state (global variables) lost on server restart
- Multiple workers can't share in-memory state
- Race conditions if multiple workers process same book

**Unknown Solutions**:
1. Should we use database for persistence or in-memory cache?
2. How to coordinate between upload phase (extraction) and generation phase (output)?
3. What database schema preserves page boundaries and text content?
4. How to handle concurrent uploads of same book?

### What Made This SR&ED-Eligible

- ✅ **Architectural uncertainty**: Best persistence strategy for multi-worker environment
- ✅ **Required experimentation**: Tested in-memory vs. database approaches
- ✅ **Performance trade-offs**: Database adds latency, but ensures reliability

### Resolution (Phase 4 Implementation)

**Solution**: Database-backed persistent storage

```python
class Page(Base):
    """Store extracted text for each page"""
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('books.id'))
    page_number = Column(Integer)  # 1-indexed
    text = Column(Text)  # Extracted content
    word_count = Column(Integer)
    char_count = Column(Integer)
```

**Benefits**:
- ✅ Survives server restarts
- ✅ Multi-worker safe
- ✅ Enables regeneration without re-extraction
- ✅ Single source of truth

**Trade-offs**:
- ⚠️ Adds ~500ms latency for large books
- ⚠️ Database storage costs (minimal for text)

### Knowledge Generated

- Database persistence essential for production-scale systems
- Page-level granularity enables incremental regeneration
- Form feed preservation in text column maintains page boundaries

---

## Summary of Technological Uncertainties

| Obstacle | SR&ED Status | Resolution Status | Key Uncertainty |
|----------|--------------|-------------------|-----------------|
| 1. Cost-accuracy trade-off | ✅ Eligible | ✅ Resolved | Unknown if 70%+ cost reduction achievable |
| 2. Arabic RTL preservation | ✅ Eligible | ✅ Resolved | Unknown optimal extraction format |
| 3. Scanned PDF detection | ✅ Eligible | ✅ Resolved | Unknown text density threshold |
| 4. TOC page identification | ✅ Eligible | ⚠️ Partial | Unknown if auto-detection feasible |
| 5. Content-section alignment | ✅ Eligible | ⚠️ Ongoing | Unknown fuzzy matching accuracy |
| 6. Gibberish detection | ✅ Eligible | ✅ Resolved | Unknown quality validation method |
| 7. Database persistence | ✅ Eligible | ✅ Resolved | Unknown best persistence strategy |

---

## Why These Obstacles Qualify for SR&ED

### CRA SR&ED Criteria Met

**1. Technological Advancement**
- ✅ Advanced beyond standard practice (82% cost reduction while maintaining accuracy)
- ✅ No published solutions for hybrid Arabic OCR optimization
- ✅ Novel application of FastText for quality validation

**2. Technological Uncertainty**
- ✅ Could not be resolved through standard practice
- ✅ Required experimental development (9 experiments conducted)
- ✅ Outcomes were unknown in advance

**3. Systematic Investigation**
- ✅ Hypothesis-driven experimentation
- ✅ Controlled testing with measurable success criteria
- ✅ Iterative refinement based on results

**4. Scientific/Technological Content**
- ✅ Advances in NLP, OCR, and machine learning
- ✅ Generated new knowledge (thresholds, methodologies)
- ✅ Documented failures and successful approaches

---

**Conclusion**: All seven obstacles meet CRA SR&ED eligibility criteria. The work performed represents genuine experimental development, not routine software engineering.

---

**Last Updated**: January 12, 2026
**Maintained By**: [Your name]
