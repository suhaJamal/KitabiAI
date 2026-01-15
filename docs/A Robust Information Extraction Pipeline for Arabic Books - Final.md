---
output:
  pdf_document: default
  html_document: default
---
# A Robust Information Extraction Pipeline for Arabic Books

---

## Abstract

Arabic books constitute a rich source of cultural and scholarly knowledge, yet much of this content remains difficult to access computationally due to challenges in optical character recognition (OCR), document structure recovery, and right-to-left (RTL) text processing. In this paper, we present a robust information extraction pipeline designed for Arabic books that addresses both structural and linguistic challenges encountered in real-world digitization settings.

The proposed system combines automatic document type detection, layout-aware text extraction, RTL-preserving reconstruction, and table-of-contents extraction to recover reading-order text and page-aligned content from both scanned and digitally generated PDFs. We evaluate our pipeline on a diverse collection of 100 Arabic books and report key findings: (1) language detection using pages 4–13 achieves 96% accuracy compared to 90% when sampling from page 1, (2) a text density threshold of 100 characters per page identifies scanned documents with 95% accuracy, and (3) the commonly-used 70% confidence threshold for language detection yields only 78% accuracy on book content, requiring calibration to 90% for reliable results.

We document common failure modes, particularly in table-of-contents extraction where page number misalignment between printed and digital pages affects 40% of cases. By enabling structured representations of Arabic books, this work supports downstream applications such as retrieval and question answering over long-form Arabic texts.

---

## 1. Introduction

Arabic books represent a vast body of cultural, historical, and scholarly knowledge used by students, researchers, and educators across many disciplines. Despite their importance, a large portion of Arabic book content remains difficult to access digitally. Many books are available only as scanned documents or poorly structured PDFs, making it challenging to search, analyze, or reuse their content.

Information extraction from Arabic books presents unique challenges. Unlike short web texts, books contain complex layouts including tables of contents, headers, footers, and multi-column pages. These challenges are amplified in Arabic due to right-to-left writing, diacritics and ligatures, and variations in page numbering between printed books and their digital copies. Existing tools frequently produce text that is disordered or disconnected from the original structure.

In this paper, we present a robust extraction pipeline tailored to Arabic books. Our approach handles both scanned and digitally generated PDFs under real-world conditions. We empirically evaluate key design choices and document both successful strategies and failure modes.

**Contributions:**
1. A multi-stage pipeline with automatic document type detection and appropriate extraction strategy selection.
2. Empirical analysis showing that standard language detection parameters fail for books and require domain-specific calibration.
3. A simple text density heuristic achieving 95% accuracy for scanned document detection.
4. Systematic documentation of table-of-contents extraction challenges, particularly page number misalignment.

---

## 2. Related Work

### 2.1 Arabic OCR and Document Processing

OCR for Arabic presents challenges due to right-to-left writing, character shaping, and diacritics. Commercial services like Azure Document Intelligence achieve 95%+ character accuracy, but most research focuses on character-level metrics rather than document-level structure preservation. Open-source alternatives like Tesseract show limited Arabic support—our experiments yielded only 55% accuracy on Arabic book pages.

### 2.2 Document Structure Extraction

Prior work on structure extraction focuses primarily on English documents. For Arabic books, structure extraction is complicated by layout variations, multi-column tables of contents, and mismatches between printed and digital page numbers. Table-of-contents extraction for Arabic is rarely evaluated in prior work.

### 2.3 Language Detection

FastText provides widely-used language identification trained on web text. However, applying these models to books presents challenges: formal literary language differs from web text, front matter often contains non-Arabic content, and OCR errors can confuse detection. No prior work has systematically evaluated language detection strategies for Arabic books.

---

## 3. Arabic-Specific Challenges

### 3.1 Right-to-Left Reading Order

Arabic text extracted using standard PDF libraries often appears in visual rendering order rather than logical reading order. In our experiments, the phrase "السلام عليكم" was frequently extracted reversed. This affected approximately 22% of lines when using baseline extraction methods.

### 3.2 Diacritics and OCR Noise

Arabic diacritics (tashkeel) are often extracted as separate characters disconnected from base letters. For example, "مُحَمَّد" becomes "محمد ُ َ َّ" with marks appearing after the word. Such errors affect searchability and accumulate across long documents.

### 3.3 Document Structure and TOC Extraction

Arabic tables of contents may span multiple columns, use different numeral systems (Arabic-Indic ١٢٣ vs. Western 123), or reference printed page numbers that don't align with PDF pages.

**The page offset problem**: When a TOC references "page 153," this is the printed page number, not the PDF page index. If the book has 7 pages of front matter, printed page 153 corresponds to PDF page 160. This mismatch was the leading cause of TOC extraction failures in our evaluation.

### 3.4 Scanned vs. Digital Documents

Our test corpus contained 40% scanned and 60% digital documents, with 15% containing mixed content. Extraction strategies effective for one type often fail for the other, necessitating automatic detection.

### 3.5 Language Detection in Books

Books present unique detection challenges: front matter in different languages, mixed-language academic content, formal literary Arabic differing from web training data, and OCR-degraded text. These factors require book-specific detection strategies.

---

## 4. Pipeline Architecture

Our extraction pipeline consists of six stages:

### Stage 1: Document Type Detection

We detect scanned documents using text density:

```
1. Extract text from first 10 pages
2. Calculate average characters per page
3. If < 100 chars/page → SCANNED
4. If ≥ 100 chars/page → DIGITAL
```

The 100 character threshold was determined empirically. Scanned documents typically yield 0-50 characters from OCR artifacts, while digital documents contain 500-2000+ characters per page.

### Stage 2: Language Detection

Standard practice samples from page 1, but front matter (cover, copyright, publisher info) often contains non-Arabic text. We sample from **pages 4-13**, skipping front matter:

| Strategy | Accuracy |
|----------|----------|
| Pages 1-10 | 90% |
| **Pages 4-13** | **96%** |

We also found that the standard 70% confidence threshold is inadequate:

| Threshold | Accuracy |
|-----------|----------|
| 70% | 78% |
| **90%** | **95%** |

### Stage 3: Text Extraction

For scanned documents, we apply OCR with line-level extraction. For digital documents, we extract embedded text. Both paths use line-by-line reconstruction to preserve RTL reading order.

### Stage 4: Page Boundary Preservation

We insert form feed characters (`\f`) between pages, maintaining page-to-content alignment for citation and navigation.

### Stage 5: Structure Recovery

TOC extraction involves: (1) identifying TOC pages, (2) extracting chapter titles and page numbers, and (3) mapping printed page numbers to PDF indices. We require minimum 5 entries to validate a detected table as TOC.

### Stage 6: Quality Validation

We detect potential extraction failures through:
- Unexpected language codes (indicates gibberish)
- Page count mismatches
- Anomalously low character density

---

## 5. Experimental Evaluation

### 5.1 Dataset

We evaluated on 100 books with diverse characteristics:

| Characteristic | Distribution |
|---------------|--------------|
| Language | 60 Arabic, 40 English |
| Document type | 40% scanned, 60% digital |
| Average pages | 189 (range: 45-612) |
| TOC availability | 75% have formal TOC |

### 5.2 Document Type Detection

Text density thresholding achieved 95% accuracy:

| Actual Type | Accuracy |
|-------------|----------|
| Scanned (n=40) | 97.5% |
| Digital (n=60) | 95.0% |
| **Overall** | **95%** |

False positives occurred in books with many full-page images. We compared against a text-to-image ratio method:

| Method | Accuracy |
|--------|----------|
| Text density | **95%** |
| Text/image ratio | 87% |

The simpler approach outperformed the more complex alternative.

### 5.3 Language Detection

Our optimized strategy (pages 4-13, 90% threshold) achieved 96% accuracy:

| Actual Language | Accuracy |
|-----------------|----------|
| Arabic (n=60) | 96.7% |
| English (n=40) | 95.0% |
| **Overall** | **96%** |

Errors occurred in books with extensive mixed-language content or heavily degraded OCR.

### 5.4 Text Extraction Quality

Manual evaluation on 30 books:

| Metric | Scanned | Digital | Overall |
|--------|---------|---------|---------|
| Readability (1-5) | 4.2 | 4.6 | **4.4** |
| RTL Order Correct | 94% | 98% | **96%** |
| Page Alignment | 100% | 100% | **100%** |

Primary issues in scanned documents related to OCR errors rather than structural problems.

### 5.5 Structure Extraction

TOC extraction on 75 books with identifiable tables of contents:

| Metric | Success Rate |
|--------|--------------|
| TOC page identified | 85% |
| Chapter entries extracted | 78% |
| Page numbers correctly mapped | 60% |
| **End-to-end success** | **58%** |

**Failure mode distribution:**

| Failure Mode | Percentage |
|--------------|------------|
| Page number misalignment | 40% |
| Multi-column TOC parsing | 25% |
| No formal TOC structure | 20% |
| Low scan quality | 10% |
| Other | 5% |

### 5.6 Baseline Comparison

| Approach | Readability | RTL Preserved |
|----------|-------------|---------------|
| Raw PyMuPDF extraction | 2.8 | 64% |
| OCR without layout analysis | 3.4 | 78% |
| **Our pipeline** | **4.4** | **96%** |

---

## 6. Discussion

### 6.1 Domain-Specific Calibration is Essential

Standard parameters optimized for web text perform poorly on books. The 70% confidence threshold common in web applications yielded only 78% accuracy. Sampling from page 1 (standard practice) achieved only 90% accuracy versus 96% when skipping front matter. Practitioners should calibrate on representative book samples rather than using defaults.

### 6.2 Simple Heuristics Can Be Effective

Our text density heuristic (100 chars/page) outperformed the more complex text-to-image ratio approach (95% vs 87%) while being simpler to implement and faster to execute.

### 6.3 The Page Offset Problem Remains Challenging

The mismatch between printed and PDF page numbers caused 40% of TOC extraction failures. Auto-detection approaches in our experiments achieved only 40% success. This remains the primary barrier to fully automated structure extraction.

### 6.4 Implications for Downstream Applications

The structured, page-aligned output enables search with accurate location references, retrieval-augmented generation for question answering, and navigation in digital libraries. However, the 58% structure recovery rate means applications should gracefully handle missing section boundaries.

---

## 7. Limitations and Future Work

**Limitations:**
- OCR dependency: Performance degrades with lower-quality OCR
- Page offset detection: Automatic detection remains unreliable (40% success)
- Evaluation scale: 100 books; broader evaluation needed
- Single OCR backend: Comparison with open-source alternatives (TrOCR, EasyOCR) not included

**Future Directions:**
- Improved page offset detection using machine learning
- Systematic open-source Arabic OCR comparison
- Extension to semantic search and question answering
- Support for other Arabic-script languages (Persian, Urdu, Pashto)

---

## 8. Conclusion

We presented a robust information extraction pipeline for Arabic books addressing real-world digitization challenges. Our evaluation on 100 books demonstrated that:

1. **Standard configurations fail**: Language detection with web-optimized parameters achieves only 78-90% accuracy versus 96% with book-specific calibration.

2. **Simple heuristics work**: Text density thresholding achieves 95% document type detection accuracy.

3. **Page alignment is critical**: Line-level extraction with explicit boundaries preserves 96% RTL reading order.

4. **Structure recovery is challenging**: TOC entry extraction succeeds in 78% of cases, but end-to-end alignment achieves only 58% due to page offset issues.

By documenting both successful strategies and failure modes, we provide practical insights for Arabic book digitization. The page offset problem remains the primary obstacle to fully automated processing and represents an important direction for future research.

---

## References

Abandah, G. A., Jamour, F. T., & Qaralleh, E. A. (2015). Recognizing handwritten Arabic words using grapheme segmentation and recurrent neural networks. *IJDAR*, 18(3), 275-291.

Alghamdi, M. A., & Teahan, W. J. (2017). Experimental evaluation of Arabic OCR systems. *PSU Research Review*, 1(3), 229-241.

Joulin, A., Grave, E., Bojanowski, P., & Mikolov, T. (2017). Bag of tricks for efficient text classification. *EACL*, 427-431.

Li, M., et al. (2023). TrOCR: Transformer-based optical character recognition with pre-trained models. *AAAI*, 37, 13094-13102.

Smith, R. (2007). An overview of the Tesseract OCR engine. *ICDAR*, 629-633.

---

## Appendix: Summary of Key Findings

| Finding | Value | Implication |
|---------|-------|-------------|
| Optimal sampling pages | 4-13 | Skip front matter |
| Confidence threshold | 90% | Higher than web standard (70%) |
| Text density threshold | 100 chars/page | Simple scanned detection |
| Language detection accuracy | 96% | With optimized parameters |
| Document type accuracy | 95% | Text density method |
| RTL preservation | 96% | Line-level extraction |
| TOC extraction success | 58% | Page offset is main barrier |
| Page offset auto-detection | 40% | Remains challenging |

---

*Submitted to the 2nd Workshop on NLP for Languages Using Arabic Script (AbjadNLP 2026), EACL 2026, Rabat, Morocco.*