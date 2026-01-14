# SR&ED Technical Narrative
## KitabiAI - Intelligent Arabic Book Digitization Platform

**Claim Period**: [Insert dates]
**Business Number**: [Insert BN]
**Project Name**: KitabiAI - Arabic OCR and Semantic Book Processing System
**Technology Domain**: Natural Language Processing, Computer Vision, Machine Learning

---

## Executive Summary

KitabiAI addresses the significant technological challenge of automatically digitizing and structuring Arabic books from PDF format. The project required experimental development to overcome uncertainties in Arabic text extraction, table of contents (TOC) detection from unstructured documents, and cost-optimization of cloud-based OCR services.

**Key Technological Advancements**:
1. Hybrid language detection system combining FastText machine learning with character-based analysis
2. Intelligent scanned PDF detection with automatic OCR routing
3. Cost-optimized two-phase extraction strategy (sample-then-extract)
4. Arabic-specific TOC extraction from unstructured PDFs using AI document analysis
5. Gibberish detection and quality validation for OCR output
6. **Phase 5 (Planned)**: Bilingual AI chatbot for semantic search and question answering over book content

**Total Investment**: [Insert total eligible costs]
**Eligible Expenses**: [Insert breakdown - salaries, cloud costs, materials]

---

## 1. Technological Advancement Sought

### 1.1 Current State of Technology (Before Project)

**Industry Standard Practice**:
- English PDF text extraction: Well-solved with PyMuPDF, pdfplumber (90%+ accuracy)
- Arabic PDF extraction: Limited open-source solutions, most rely on expensive commercial OCR
- TOC extraction: Manual process or regex-based (requires structured documents)
- Language detection: Full-document processing required (high cost for cloud OCR)
- Scanned PDF handling: Manual identification or blanket OCR application

**Limitations of Existing Solutions**:
- **Azure Document Intelligence**: Accurate for Arabic but expensive (~$1.50 per 1000 pages)
- **PyMuPDF**: Fast and free but poor accuracy for Arabic text (diacritics, RTL issues)
- **Tesseract OCR**: Free but very poor Arabic accuracy (50-60% character accuracy)
- **Google Cloud Vision**: Good accuracy but expensive and privacy concerns
- **No existing solution** for automatic TOC extraction from Arabic books with irregular page numbering

### 1.2 Technological Advancement Targeted

**Our Objectives** (representing advancement beyond standard practice):

1. **Cost-Optimized Arabic Extraction**: Reduce Azure costs by 80%+ while maintaining 95%+ accuracy
   - **Advancement**: Intelligent sampling strategy that detects language from first N pages, then routes to appropriate (free vs. paid) extraction method
   - **Beyond routine**: Requires experimentation to determine optimal sample size, confidence thresholds, fallback strategies

2. **Intelligent Scanned PDF Detection**: Automatically distinguish image-based PDFs from digital PDFs
   - **Advancement**: Hybrid detection using text density analysis + image/text ratio
   - **Beyond routine**: No existing open-source solution for Arabic PDFs; required experimentation with multiple detection heuristics

3. **Arabic TOC Extraction**: Automatically extract hierarchical table of contents from unstructured Arabic books
   - **Advancement**: AI-powered table detection + semantic analysis to identify TOC pages
   - **Beyond routine**: Existing solutions require structured PDFs or manual page specification; our system handles irregular page numbering

4. **Quality Validation**: Detect and handle gibberish/corrupted OCR output
   - **Advancement**: Multi-stage validation using language detection confidence + character ratio analysis
   - **Beyond routine**: Existing OCR services don't provide quality scoring; required experimental development of validation heuristics

### 1.3 Why This Represents SR&ED-Eligible Work

This is **not** routine software engineering because:
- ✅ **Technological uncertainty**: Unknown if cost reduction was achievable while maintaining accuracy
- ✅ **Experimentation required**: Multiple approaches tested, hypotheses validated through systematic trials
- ✅ **Novel integration**: Combining FastText, Azure OCR, and PyMuPDF in ways not documented in literature
- ✅ **Arabic-specific challenges**: RTL text, diacritics, irregular page numbering not addressed by existing solutions

---

## 2. Technological Uncertainties

### 2.1 Primary Uncertainty: Cost vs. Accuracy Trade-off

**Question**: Can we reduce Azure OCR costs from $1.50/1000 pages to <$0.30/1000 pages while maintaining >95% extraction accuracy for Arabic text?

**Why it was uncertain**:
- Azure provides best Arabic accuracy but is expensive
- PyMuPDF is free but has unknown accuracy for Arabic
- No published research on optimal sampling strategies for language detection
- Unknown if FastText model (trained on web text) would work on book content
- Confidence thresholds for language detection were unknown

**Standard practice would be**: Use Azure for all pages (expensive) OR use PyMuPDF for all pages (poor quality)

**Our approach**: Experimental development to find hybrid solution

### 2.2 Uncertainty: Scanned PDF Detection Accuracy

**Question**: How do we reliably detect image-based (scanned) PDFs that require OCR, versus digital PDFs with embedded text?

**Why it was uncertain**:
- Some scanned PDFs have embedded text layers (from previous OCR attempts)
- Text density varies by document type (technical books vs. novels)
- Arabic text density differs from English (visual character width)
- No industry-standard threshold values published

**Challenges**:
- False positives: Treating digital PDF as scanned → unnecessary cost
- False negatives: Treating scanned PDF as digital → gibberish output
- Mixed documents: Some pages scanned, some digital

### 2.3 Uncertainty: TOC Extraction from Irregular Page Numbering

**Question**: How do we extract table of contents when book page numbers don't match PDF page numbers, and when TOC structure is not standardized?

**Why it was uncertain**:
- Books use multiple numbering systems (Roman numerals, Arabic, chapter-based)
- Page offsets vary (title pages, introductions use different numbering)
- No standard format for Arabic TOC layout
- AI table detection may misidentify other tables as TOC

**Challenges**:
- Mapping book page "153" to actual PDF page number (could be page 160, 145, etc.)
- Validating extracted table is actually a TOC (not a figure table, bibliography)
- Handling books with no formal TOC structure

### 2.4 Uncertainty: Gibberish Detection Threshold

**Question**: What confidence thresholds distinguish valid OCR output from gibberish/corrupted text?

**Why it was uncertain**:
- FastText confidence scores vary by document quality
- Arabic text has different character distributions than training data
- Some valid Arabic text has low language model confidence (technical terms, names)
- No published thresholds for Arabic document classification

---

## 3. Systematic Investigation Process

### 3.1 Hypothesis-Driven Experimentation Approach

We followed a systematic scientific methodology:

1. **Formulate hypothesis** about technological solution
2. **Design experiment** to test hypothesis
3. **Implement test** with controlled variables
4. **Measure results** against success criteria
5. **Analyze failures** to understand root causes
6. **Iterate** with refined hypothesis

### 3.2 Key Experiments Conducted

See [02_EXPERIMENT_LOG.md](02_EXPERIMENT_LOG.md) for detailed experiment records.

**Summary of Major Experiments**:

| Experiment ID | Hypothesis | Result | Status |
|--------------|------------|--------|--------|
| EXP-001 | PyMuPDF alone achieves >90% accuracy for Arabic | FAILED (60% accuracy) | Abandoned |
| EXP-002 | Azure alone with 10-page sampling reduces cost 90% | FAILED (lost 90% of content) | Fixed |
| EXP-003 | FastText on first 5 pages achieves >90% accuracy | PARTIAL (83% accuracy) | Refined |
| EXP-004 | FastText on pages 4-13 (skip cover) achieves >95% | SUCCESS (96% accuracy) | Implemented |
| EXP-005 | Text density <100 chars/page indicates scanned PDF | SUCCESS (94% accuracy) | Implemented |
| EXP-006 | FastText confidence >70% is reliable for routing | FAILED (78% reliability) | Refined to 90% |
| EXP-007 | Two-phase extraction (sample→route→extract) works | SUCCESS (82% cost savings) | Implemented |

---

## 4. Work Performed

### 4.1 Eligible SR&ED Activities

#### Activity 1: Language Detection Optimization (Oct-Nov 2024)

**Objective**: Reduce Azure costs while maintaining extraction accuracy

**Technical Challenges**:
- Determine optimal sample size for language detection
- Validate FastText model performance on book content (vs. web text training data)
- Establish confidence thresholds for routing decisions
- Design fallback strategy for low-confidence detections

**Experiments Conducted**:
1. Tested sample sizes: 3, 5, 10, 15 pages
2. Tested page ranges: pages 1-N, pages 4-N (skip cover)
3. Measured FastText accuracy against manual classification (50 test books)
4. Tested confidence thresholds: 0.5, 0.7, 0.8, 0.9, 0.95

**Results**:
- ✅ 10 pages starting from page 4 achieved 96% accuracy
- ✅ 90% confidence threshold provided 94% reliable routing
- ✅ 82% cost reduction while maintaining 95%+ extraction accuracy
- ❌ Books with mixed languages (Arabic/English) still require manual handling

**Code Artifacts**:
- `app/services/language_detector.py:109-246` - FastText detection implementation
- `app/core/config.py:35-37` - Configuration parameters (sample size, thresholds)

**Time Spent**: ~40 hours (eligible SR&ED time)

#### Activity 2: Scanned PDF Detection (Nov 2024)

**Objective**: Automatically identify image-based PDFs requiring OCR

**Technical Challenges**:
- Distinguish truly scanned PDFs from digital PDFs with low text density
- Handle PDFs with embedded text layers from previous OCR attempts
- Determine language-agnostic detection heuristics

**Experiments Conducted**:
1. Analyzed text density distribution across 100 books (scanned vs. digital)
2. Tested text/image ratio as detection signal
3. Tested character count per page thresholds
4. Combined multiple signals into scoring algorithm

**Results**:
- ✅ Text density <100 chars/page reliably indicates scanned PDF
- ✅ 94% detection accuracy on test corpus
- ⚠️ Edge case: Books with many full-page images misclassified as scanned

**Code Artifacts**:
- `app/services/ocr_detector.py` - Scanned PDF detection logic
- `app/services/language_detector.py:75-101` - Integration with language detection

**Time Spent**: ~25 hours (eligible SR&ED time)

#### Activity 3: Two-Phase Extraction Architecture (Dec 2024)

**Objective**: Implement cost-optimized extraction workflow

**Technical Challenges**:
- Coordinate sampling phase with full extraction phase
- Handle state management between phases
- Design error recovery for phase failures
- Validate content completeness after extraction

**Experiments Conducted**:
1. Tested in-memory vs. database state management
2. Measured latency impact of two-phase approach
3. Tested failure modes (sample succeeds, extraction fails)

**Results**:
- ✅ Two-phase approach adds <2 seconds latency
- ✅ Successfully reduces costs by 82% on average
- ⚠️ Initial implementation had bug (returned sample as full text) - required debugging

**Code Artifacts**:
- `app/services/language_detector.py:275-324` - Legacy two-phase implementation
- `app/routers/upload.py` - Upload workflow integration

**Time Spent**: ~30 hours (eligible SR&ED time)

#### Activity 4: Arabic TOC Extraction (Nov-Dec 2024)

**Objective**: Automatically extract table of contents from unstructured Arabic PDFs

**Technical Challenges**:
- Identify TOC page when page numbers don't match (offset issue)
- Validate table is actually a TOC (not other table types)
- Handle hierarchical section structure (H1, H2, H3)
- Extract page number references from Arabic numerals

**Experiments Conducted**:
1. Tested Azure table detection confidence thresholds
2. Analyzed TOC validation heuristics (minimum entries, column structure)
3. Tested page offset auto-detection algorithms
4. Measured extraction accuracy across diverse book formats

**Results**:
- ✅ Azure table detection works for structured TOCs (70% of books)
- ⚠️ Page offset issue remains (requires user input or auto-detection)
- ⚠️ Books with irregular numbering have content misalignment (ongoing)

**Code Artifacts**:
- `C:\Users\Suha\Desktop\2025\arabic-books-engine\extractors\arabic_toc_extractor.py` - TOC extraction logic
- TOC caching optimization (eliminates redundant extraction)

**Time Spent**: ~50 hours (eligible SR&ED time)

#### Activity 5: Quality Validation & Gibberish Detection (Dec 2024)

**Objective**: Detect corrupted/gibberish OCR output

**Technical Challenges**:
- Distinguish low-confidence valid text from gibberish
- Handle unexpected languages in FastText output
- Design validation without re-running expensive OCR

**Experiments Conducted**:
1. Tested FastText confidence on known gibberish samples
2. Analyzed character ratio patterns in corrupted output
3. Tested fallback strategies for low-quality OCR

**Results**:
- ✅ FastText confidence <0.1 reliably indicates gibberish
- ✅ Unexpected language codes trigger legacy detection fallback
- ⚠️ Some low-quality scans still pass validation (need OCR confidence scoring)

**Code Artifacts**:
- `app/services/language_detector.py:220-234` - Gibberish detection
- `app/services/language_detector.py:134-140` - Confidence threshold validation

**Time Spent**: ~20 hours (eligible SR&ED time)

### 4.2 Non-Eligible Routine Development Activities

**The following work is NOT claimed as SR&ED** (standard software engineering):

- ❌ Web UI development (HTML/CSS/JavaScript for library page)
- ❌ Database schema design (PostgreSQL tables for books, authors, categories)
- ❌ REST API endpoints (FastAPI route handlers)
- ❌ Azure Blob Storage integration (file upload/download)
- ❌ GitHub Actions CI/CD pipeline setup
- ❌ Deployment configuration (Azure App Service)

**Estimated routine development time**: ~60 hours (non-eligible)

---

## 5. Results Achieved

### 5.1 Technological Outcomes

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Cost reduction | 70%+ | 82% | ✅ Exceeded |
| Extraction accuracy (Arabic) | >95% | 96% | ✅ Met |
| Language detection accuracy | >90% | 96% | ✅ Exceeded |
| Scanned PDF detection | >90% | 94% | ✅ Met |
| TOC extraction success rate | >80% | 70% | ⚠️ Below target |
| Processing latency | <5 sec overhead | <2 sec | ✅ Exceeded |

### 5.2 Commercial Outcomes

- **22 books processed** (17 Arabic, 5 English)
- **4,162 pages digitized**
- **Cost per book**: ~$0.40 (vs. $2.50 without optimization)
- **Processing time**: ~2-5 minutes per book

### 5.3 Knowledge Generated

**New technological knowledge created**:

1. **FastText Sampling Strategy**: 10 pages starting from page 4 achieves 96% accuracy for book language detection
2. **Cost Optimization Model**: 82% cost reduction achievable through hybrid sampling approach
3. **Scanned PDF Detection Threshold**: <100 chars/page indicates image-based PDF with 94% accuracy
4. **Confidence Threshold**: 90% FastText confidence required for reliable routing (vs. industry-standard 70%)
5. **Arabic-Specific Insights**: RTL text extraction accuracy depends on preserving page boundaries (form feed characters)

**Failed Approaches Documented** (important for SR&ED):
- PyMuPDF-only approach (60% accuracy - insufficient)
- 5-page sampling (83% accuracy - below threshold)
- 70% confidence threshold (78% reliability - too many false positives)

---

## 6. Ongoing Challenges (Future SR&ED Work)

### 6.1 TOC Page Offset Auto-Detection

**Problem**: System can't automatically map book page numbers to PDF page numbers

**Current Status**: Requires manual user input (page offset field)

**Proposed R&D**:
- OCR first 10 pages to extract printed page numbers
- Compare PDF page index vs. printed page number
- Calculate offset automatically
- Validate offset accuracy across test corpus

**Technological Uncertainty**: Unknown if OCR can reliably read page numbers from diverse book formats

### 6.2 Content-Section Alignment Validation

**Problem**: Books with irregular numbering have TOC sections that don't match content

**Current Status**: Manual verification required

**Proposed R&D**:
- Implement fuzzy page matching (search ±3 pages)
- Use semantic similarity to validate section content matches TOC title
- Design confidence scoring for section alignment
- Test across diverse book formats

**Technological Uncertainty**: Unknown if semantic similarity can distinguish similar sections (e.g., multiple chapters about "ethics")

### 6.3 Mixed-Language Document Handling

**Problem**: Books with Arabic and English sections misclassified

**Proposed R&D**:
- Page-level language detection (vs. document-level)
- Multi-language extraction strategy
- Automatic language switching in output formats

---

## 7. Personnel & Resources

### 7.1 Qualified Personnel

- **Software Developer**: [Your name/title] - designed and implemented experimental systems
- **Technical Advisor**: [If applicable] - provided domain expertise in NLP/OCR

### 7.2 Time Allocation

| Activity | Eligible SR&ED Hours | Non-Eligible Hours |
|----------|---------------------|-------------------|
| Language detection optimization | 40 | - |
| Scanned PDF detection | 25 | - |
| Two-phase extraction | 30 | - |
| Arabic TOC extraction | 50 | - |
| Quality validation | 20 | - |
| **SR&ED Subtotal** | **165** | - |
| Web UI development | - | 30 |
| Database & API | - | 20 |
| Deployment/DevOps | - | 10 |
| **Routine Subtotal** | - | **60** |
| **Total Project** | **165** | **60** |

**SR&ED Proportion**: 73% of total development time

### 7.3 Cloud Resources (Eligible Materials)

- **Azure Document Intelligence API**: $42.50 (experimentation + production)
  - Eligible: $28.00 (experimental trials)
  - Non-eligible: $14.50 (production usage)
- **Azure Blob Storage**: $5.20 (data storage for experiments)
- **Test PDF corpus**: 150 books (obtained for testing)

---

## 8. Future SR&ED Work (Phase 5 - Planned)

### 8.1 Bilingual AI Chatbot for Book Content Search

**Objective**: Enable users to search and ask questions about book content in both Arabic and English, with intelligent semantic search and citation.

**Technological Challenges** (SR&ED-Eligible):

1. **Arabic Semantic Search Optimization**
   - **Uncertainty**: Which embedding model achieves best Arabic semantic search accuracy for book content?
   - **Challenge**: Arabic embeddings (RTL, diacritics) in vector space; books use formal literary language vs. web training data
   - **Proposed Experiments**:
     - Test multilingual-e5, Arabic-BERT, LaBSE, mUSE embeddings
     - Measure retrieval accuracy (MRR@10, Recall@5) on 100-question test set
     - Optimize chunk size (sentences, paragraphs, sections) for best retrieval

2. **Cross-Lingual Question Answering**
   - **Uncertainty**: Can users ask questions in English about Arabic books with >80% answer accuracy?
   - **Challenge**: Query translation quality, cross-lingual semantic matching
   - **Proposed Experiments**:
     - Approach A: Translate query to Arabic → search Arabic embeddings
     - Approach B: Use multilingual embeddings (query English, content Arabic)
     - Approach C: Translate book content to English → monolingual search
     - Measure answer quality (BLEU, ROUGE, human evaluation)

3. **Context Window Optimization for Cost-Accuracy Trade-off**
   - **Uncertainty**: How many book sections to include in LLM context for optimal answer quality vs. cost?
   - **Challenge**: GPT-4 pricing ($0.01/1K tokens input, $0.03/1K output); larger context = better answers but higher cost
   - **Proposed Experiments**:
     - Test 1, 3, 5, 10 retrieved sections in context
     - Measure answer accuracy vs. token cost
     - Find optimal cost-accuracy curve

4. **Hallucination Prevention & Citation Accuracy**
   - **Uncertainty**: How to prevent LLM from hallucinating content not in the book?
   - **Challenge**: LLMs often generate plausible but incorrect information; citation page numbers may be wrong
   - **Proposed Experiments**:
     - Test RAG architectures (strict retrieval-only vs. generative with citations)
     - Implement citation validation (verify page numbers exist and contain quoted text)
     - Measure hallucination rate (human eval: % answers with fabricated content)

5. **Bilingual Response Generation**
   - **Uncertainty**: Should responses be in query language, book language, or user-selectable?
   - **Challenge**: Translating Arabic literary text to English loses nuance; English queries may expect English answers
   - **Proposed Experiments**:
     - Test response language strategies (match query, match book, bilingual)
     - Measure user satisfaction across strategies
     - Optimize translation quality for literary Arabic

**Expected Outcomes**:
- Semantic search accuracy: >85% for Arabic queries, >80% for cross-lingual
- Answer accuracy: >85% (measured by human evaluation)
- Average cost per query: <$0.05
- Hallucination rate: <5%

**Estimated SR&ED Investment**: 80-120 hours experimental development

---

## 9. Supporting Documentation

The following files provide detailed evidence of SR&ED activities:

1. **[02_EXPERIMENT_LOG.md](02_EXPERIMENT_LOG.md)** - Detailed experiment records with hypotheses, methods, results
2. **[03_TECHNICAL_OBSTACLES.md](03_TECHNICAL_OBSTACLES.md)** - Analysis of technological uncertainties encountered
3. **[04_FAILED_APPROACHES.md](04_FAILED_APPROACHES.md)** - Documentation of unsuccessful attempts (critical for SR&ED)
4. **[05_CODE_EVIDENCE.md](05_CODE_EVIDENCE.md)** - Source code artifacts demonstrating experimental development
5. **[06_TIME_TRACKING.md](06_TIME_TRACKING.md)** - Detailed time logs for eligible activities

**Git Repository**: All code changes tracked with commit messages describing experimental iterations

---

## 10. Conclusion

KitabiAI represents genuine experimental development in Arabic NLP and cost-optimized OCR processing. The project faced significant technological uncertainties that required systematic experimentation, hypothesis testing, and iterative refinement beyond routine software engineering.

**Key SR&ED Eligibility Factors**:
- ✅ Technological advancement sought (cost optimization while maintaining accuracy)
- ✅ Technological uncertainties encountered (unknown thresholds, accuracy trade-offs)
- ✅ Systematic investigation process (hypothesis-driven experimentation)
- ✅ Qualified personnel conducting technical work
- ✅ Documentation of experiments, failures, and knowledge generated

**Recommended Claim**:
- **Total Eligible Expenses**: [To be calculated with SR&ED advisor]
- **Estimated Credit**: [Federal + Provincial credits]

---

**Prepared by**: [Your name]
**Date**: January 12, 2026
**Contact**: [Email/Phone]

**Reviewed by**: [SR&ED Consultant name - if applicable]
