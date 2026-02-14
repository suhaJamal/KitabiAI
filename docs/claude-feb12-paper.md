# A Structured Arabic Book Corpus with ML-Driven Extraction and Hierarchical Chapter Indexing

## Abstract

Arabic books represent a vast repository of cultural and scholarly knowledge, yet significant portions remain digitally inaccessible due to OCR challenges, RTL text preservation issues, and document structure recovery complexities. We present a bilingual book digitization toolkit that creates structured, searchable Arabic book corpora with detailed chapter-level indexing. The system uses a two-phase hybrid extraction architecture: first analyzing sample pages with a local PDF parser and FastText language detection, then routing Arabic content to cloud-based OCR for RTL preservation and English content to local parsing. Beyond basic text extraction, the toolkit generates rich structural metadata including hierarchical chapter boundaries, page-aligned content, and multi-format output (HTML, Markdown, JSONL) suitable for downstream NLP tasks and semantic search applications. Key contributions include: (1) a growing structured Arabic book corpus of 24 books (4,185+ pages) with chapter-level annotations, (2) heading-based Table of Contents generation using paragraph role detection that bypasses traditional page offset problems, and (3) the use of unexpected language predictions as a practical indicator of OCR extraction quality, triggering automatic fallback to cloud-based verification. Evaluation on 24 Arabic and English books achieved 100% language routing accuracy while significantly reducing cloud processing costs compared to uniform cloud-based extraction. The toolkit and processed corpus will be made publicly available upon acceptance to support research in digital humanities and Arabic NLP.

## 1. Introduction

Arabic books constitute a rich and diverse body of cultural, historical, religious, and scholarly knowledge relied upon by students, researchers, and educators across many disciplines. Despite their importance, a substantial portion of Arabic book content remains difficult to access computationally. Many books exist only as scanned documents or poorly structured PDFs, making it impractical to search, analyze, or integrate their content into modern NLP pipelines. This limitation is particularly consequential given the growing interest in building Arabic language models, question-answering systems, and digital humanities applications that depend on structured training data.

Information extraction from Arabic books presents challenges distinct from those encountered with English or short web texts. Books contain complex layouts including tables of contents, running headers and footers, footnotes, and multi-column pages. These challenges are amplified in Arabic due to right-to-left text ordering, the presence of diacritics and ligatures, and systematic misalignment between printed page numbers and their corresponding positions in digital PDF files. Existing open-source tools frequently produce Arabic text that is visually reordered rather than logically sequenced, while cloud-based OCR services capable of preserving Arabic reading order introduce significant per-page processing costs. Furthermore, most digitization efforts focus on page-level text extraction without recovering the hierarchical document structure (chapters, sections, subsections) that is essential for meaningful content navigation and retrieval.

In this paper, we present a comprehensive toolkit for Arabic book digitization that addresses these challenges through ML-driven language routing and automated structure recovery. Our system automatically detects a book's language, selects the appropriate extraction method, and generates structured output with hierarchical chapter boundaries and page-aligned content. We contribute both the processing toolkit and a growing structured Arabic book corpus to the research community. The system has been deployed and evaluated on a corpus of 24 books totaling over 4,185 digitized pages, producing output in three formats optimized for different research applications.

### Contributions

1. **A Structured Arabic Book Corpus.** We contribute a growing corpus of 24 structured Arabic and English books with rich metadata including author, title, subject classification, and hierarchical table of contents. Each book is provided in three complementary formats -- responsive HTML for human reading, structured JSONL for computational analysis, and Markdown for lightweight processing -- addressing the need for openly available, structured Arabic book data suitable for NLP research and digital humanities applications.

2. **A Hybrid Extraction Architecture with ML-Driven Language Routing.** We present a two-phase processing system that combines free local parsing tools with cloud-based OCR through automatic language detection. The system uses FastText on sampled pages to determine the book's language, then routes to the appropriate extraction method. When the language model returns unexpected predictions (e.g., detecting Vietnamese or Urdu in a known-Arabic book), the system treats this as a signal of poor extraction quality and triggers cloud-based verification on a targeted page range, skipping multilingual front matter. This approach achieved 100% language routing accuracy across our evaluation corpus while substantially reducing processing costs compared to uniform cloud-based extraction.

3. **Heading-Based Table of Contents Generation.** We develop an alternative approach to TOC recovery that detects chapter titles and section headings throughout the document using paragraph role classification from the OCR engine. Unlike traditional TOC extraction, which requires locating a dedicated TOC page and manually correcting page number offsets, our heading-based approach identifies structural boundaries directly from the document content. This eliminates the page offset problem that commonly affects Arabic books where printed page numbers diverge from PDF page positions. The system applies bounding-box height filtering and content validation to distinguish genuine headings from inline text falsely classified as titles.

## 2. Related Work

Our work draws on four areas of prior research: Arabic text extraction, Arabic corpus creation, document structure recovery, and language identification for digitized content. We summarize the most relevant efforts below and highlight the gaps our toolkit addresses.

### 2.1 Arabic Text Extraction

Extracting text from Arabic documents has long been more challenging than from English ones. Open-source OCR engines such as Tesseract (Smith, 2007) support Arabic script, but frequently produce output in visual order rather than the logical reading order required for downstream processing, particularly when handling ligatures and diacritics. Commercial cloud services — including Google Cloud Vision, Amazon Textract, and Azure Document Intelligence — offer significantly better Arabic text fidelity, but introduce per-page processing costs that become prohibitive at corpus scale. Local PDF parsing libraries like PyMuPDF provide fast, free text extraction for digitally-born documents, yet they fail on scanned Arabic PDFs where no embedded text layer exists. This forces practitioners into an all-or-nothing choice: either process every page through expensive cloud OCR, or accept degraded quality from free tools. Our system avoids this trade-off by using ML-based language detection to route only Arabic content to cloud OCR, while processing English content locally at zero cost.

### 2.2 Arabic Corpora

Several Arabic corpora have been developed to support NLP research. The OSIAN corpus (Zeroual et al., 2019) provides 3.5 million articles from international Arabic news sources, while the Abu El-Khair corpus (Abu El-Khair, 2016) contains 5 million news articles across multiple domains. The KALIMAT corpus (El-Haj and Koulali, 2013) offers a smaller but carefully annotated collection of Arabic text for summarization and keyphrase extraction. These resources have been valuable for training Arabic language models and evaluating Arabic NLP tools.

However, existing Arabic corpora are predominantly drawn from news articles, Wikipedia, or web text. Book-length content — with its complex hierarchical structure, diverse genres, and extended discourse — remains underrepresented. Where digitized Arabic book collections do exist, such as the Shamela Library, they typically provide raw text without structured chapter-level annotations, page alignment, or standardized metadata. Our corpus addresses this gap by providing Arabic book content with hierarchical section boundaries, page-aligned text, and multi-format output designed for computational analysis.

### 2.3 Document Structure Recovery

Recovering the internal structure of a document — its chapters, sections, and subsections — is essential for meaningful content navigation and retrieval. Prior approaches fall into two broad categories. The first relies on extracting embedded PDF bookmarks or parsing a dedicated Table of Contents page within the document (Déjean and Meunier, 2006; Déjean and Meunier, 2009). Prior work on TOC extraction for digitized books includes Bukhari et al. (2012), who detected TOC pages in Urdu books using layout features, and Doucet et al. (2013), who extracted TOC entries from European digitized books. While effective for well-formed digital documents, these approaches assume that printed page numbers correspond to digital page indices — an assumption that frequently fails for books with unnumbered front matter. This mismatch is especially common in Arabic books, where introductory pages often use a different numbering system or are unnumbered entirely.

The second category uses layout analysis to detect structural elements from visual features. Tools like GROBID (Lopez, 2009) and systems trained on datasets such as DocBank (Li et al., 2020) and PubLayNet (Zhong et al., 2019) can identify headings, paragraphs, and figures from document images. However, these tools are primarily designed for academic papers and technical documents, not for the varied layouts found in published books.

Our approach takes a different path: rather than relying on a TOC page or training a custom layout model, we leverage paragraph role classification provided by a cloud OCR engine to identify headings throughout the document. This bypasses the page offset problem entirely, since section boundaries are determined by the actual position of headings in the PDF rather than by printed page numbers. While the page offset problem is well-known among practitioners, it has received limited attention in the literature as a distinct failure mode in Arabic book digitization. Our heading-based approach offers a practical alternative that bypasses the problem entirely.

### 2.4 Language Identification and OCR Quality

Language identification is a well-studied task, with tools like FastText's language identification model (Joulin et al., 2017) achieving strong performance across 176 languages on clean web text. However, applying language identification to OCR output introduces complications: garbled or corrupted text produced by poor extraction can confuse language classifiers, leading to unexpected predictions. Maurer (2023) studied this interaction in the context of multilingual digitized collections at the National Library of Luxembourg, showing that OCR errors significantly degrade language identification accuracy. We invert this relationship: rather than treating unexpected language predictions as a problem to minimize, we treat them as a signal of extraction failure that triggers automatic corrective action.

Prior work has also explored OCR quality assessment through language modelling approaches. Boros et al. (2022) proposed using language model perplexity as an offline quality metric for OCR evaluation at LREC 2022, while earlier work by Taghva and Stofsky (2001) developed methods for recognizing "garbage" tokens in OCR output from historical documents. Our approach differs in that it operates online within a production pipeline, using lightweight language predictions to trigger fallback processing without requiring a dedicated language model.

Concretely, when FastText returns an unexpected language code — such as Vietnamese or Urdu for a book known to be Arabic — the system interprets this as evidence that the local PDF parser produced garbled text, and automatically escalates to cloud-based OCR. This turns a known limitation of language identification on noisy text into a practical quality control mechanism within a live processing pipeline.

## 3. System Architecture

The system processes a PDF book through four sequential stages: (1) document type detection, which determines whether the PDF is scanned or digitally born; (2) language detection and extraction routing, which identifies the book's language and selects the appropriate text extraction method; (3) table of contents recovery, which identifies chapter boundaries either by parsing a dedicated TOC page or by detecting headings throughout the document; and (4) multi-format output generation, which produces HTML, JSONL, and Markdown renderings of the structured book content. All extracted text and structural metadata are persisted in a relational database at page-level granularity, enabling incremental regeneration of output formats without re-extracting from the original PDF. The following subsections describe each stage in detail.

### 3.1 Document Type Detection

Before language detection, the system determines whether a PDF contains extractable digital text or is a scanned image-only document requiring OCR. This step is critical because scanned Arabic PDFs produce no text through local parsing, which would otherwise cause the language detector to misclassify them as English (due to the absence of Arabic characters). The system samples up to 10 pages using a local PDF parser and measures text density against two thresholds: a minimum of 50 characters and 10 words per sampled page. Pages yielding text below these thresholds, or producing garbled output detected through a gibberish filter, are counted as text-free. If the sampled pages contain insufficient text, the PDF is classified as scanned and routed directly to cloud-based OCR, bypassing the local extraction path entirely.

### 3.2 Language Detection and Routing

Language detection follows a two-phase sampling strategy designed to minimize cloud OCR costs:

**Phase 1 -- Language Sampling (Pages 4-13):** The system extracts text from a sample of 10 pages using a local PDF parser, skipping the first three pages which typically contain cover art, publisher information, and multilingual front matter that could confuse detection. The extracted text is analyzed using a pre-trained FastText language identification model (176 languages). If the confidence score falls below the calibrated threshold, the system falls back to a character-ratio analysis that counts Arabic Unicode characters relative to Latin characters.

**Phase 2 -- Full Extraction Routing:** Based on the detected language, the system routes to the appropriate extraction method:
- **Arabic content:** Cloud-based OCR with line-by-line extraction to preserve RTL reading order and diacritics.
- **English content:** Local PDF parsing using PyMuPDF, which provides accurate extraction for left-to-right digital text at zero cost.

**Quality Detection via Unexpected Languages:** During Phase 1, if FastText returns a language code other than Arabic (`ar`) or English (`en`) -- such as Vietnamese, French, or Urdu -- the system interprets this as a signal that the local PDF parser produced garbled text (common with scanned Arabic documents). In such cases, the system automatically escalates to cloud-based OCR verification on pages 11-25, bypassing potential noise from front matter.

### 3.3 Table of Contents Recovery

The system offers two complementary approaches to TOC recovery:

**Method 1 -- Extraction from Book:** For books containing a dedicated TOC page, the system extracts chapter titles and page numbers using pattern matching (English) or table structure recognition (Arabic via cloud OCR). This method requires the user to specify the TOC page location and an optional page offset to correct the numbering mismatch between printed and PDF pages.

**Method 2 -- Generation from Headings:** For books without a formal TOC or where page offsets are unknown, the system scans all pages for paragraphs classified as `title` or `sectionHeading` by the cloud OCR engine's paragraph role detection. Detected headings are filtered using:
- **Bounding-box height filtering:** Paragraphs with normalized height below 0.025 are excluded to remove small inline text falsely tagged as headings.
- **Numeric content filtering:** Purely numeric content (including Arabic-Indic numerals) is excluded to avoid detecting page numbers as chapter titles.
- **Length validation:** Headings shorter than 3 characters or longer than 200 characters are excluded.

Section boundaries are calculated from heading positions, with each section spanning from its heading to the next heading or end of document.

### 3.4 Multi-Format Output Generation

Each processed book is output in three formats:
- **HTML:** Responsive web pages with full RTL support, CSS styling, and navigable chapter structure for human readers.
- **JSONL:** Page-level and section-level structured data with metadata fields for computational processing, search indexing, and NLP pipeline integration.
- **Markdown:** Lightweight structured text with heading hierarchy (H1-H3) for documentation and text analysis tools.

## 4. The Arabic Book Corpus

### 4.1 Corpus Composition

The current corpus comprises 24 books (13 Arabic, 11 English) spanning diverse genres including Islamic studies, history, literature, and academic texts. The corpus includes both modern digital publications and older scanned documents with varying layout quality.

| Statistic | Value |
|---|---|
| Total books | 24 |
| Arabic books | 13 |
| English books | 11 |
| Total pages digitized | 4,185+ |
| Total sections extracted | 750+ |
| Output formats per book | 3 (HTML, JSONL, Markdown) |

### 4.2 Corpus Structure

Each book entry in the corpus includes:
- **Metadata:** Title, author, language, subject category, keywords, ISBN (where available), publication date, page count.
- **Full text:** Page-aligned extracted text preserving the original reading order.
- **Chapter structure:** Hierarchical section boundaries with title, level (1-3), start page, and end page.
- **Format variants:** HTML, JSONL, and Markdown renderings of the full book content.

The corpus is stored in a relational database (PostgreSQL) with five tables: books, authors, categories, pages, and sections. This structure enables efficient querying, filtering by language or category, and incremental corpus expansion.

### 4.3 Corpus Availability

The corpus will be made publicly available upon acceptance, hosted as downloadable JSONL files with accompanying metadata. The processing toolkit will be released as open-source software to enable researchers to process additional Arabic books using the same pipeline. The corpus is designed for ongoing growth, with new open-source Arabic books added as they become available.

## 5. Evaluation

### 5.1 Language Routing Accuracy

We evaluated language routing on all 24 books in the corpus. Each book's detected language was verified against the known ground truth (the actual language of the book as confirmed by manual inspection).

| Metric | Result |
|---|---|
| Books evaluated | 24 |
| Correct language routing | 24/24 (100%) |
| Arabic books correctly routed to cloud OCR | 13/13 |
| English books correctly routed to local parsing | 11/11 |

The quality detection mechanism (unexpected language codes) was triggered on 3 occasions during development, each time correctly identifying cases where the local parser produced garbled output from scanned Arabic PDFs.

### 5.2 Cost Reduction

By routing English books to free local parsing and using targeted page sampling for language detection, the system avoids cloud OCR processing for all English books entirely. For the 11 English books in our corpus (approximately 1,900 pages), this represents a direct cost saving compared to processing all pages through cloud OCR.

### 5.3 TOC Generation Quality

[To be completed with qualitative analysis of heading detection accuracy across different book types. Discuss cases where bounding-box filtering improved results and remaining challenges with books that have unconventional layouts.]

### 5.4 Limitations

- The corpus size (24 books) is modest; we plan to expand it with additional open-source Arabic content.
- TOC generation accuracy has not been formally evaluated with precision/recall metrics against manually annotated ground truth. We report qualitative observations.
- The confidence threshold for language detection (currently set at 50%) was determined through iterative development rather than systematic grid search. A formal threshold analysis across a larger book collection would strengthen this finding.
- The system currently supports Arabic and English only. Extension to other RTL languages (Persian, Urdu) would require additional validation.

## 6. Conclusion and Future Work

We presented a bilingual book digitization toolkit and structured Arabic book corpus designed to make Arabic book content computationally accessible. The system combines ML-driven language routing with automated document structure recovery to produce structured, multi-format output from PDF books. Our evaluation on 24 books demonstrated 100% language routing accuracy while substantially reducing processing costs through intelligent extraction method selection.

The toolkit and corpus address a practical gap in Arabic NLP resources: the availability of structured, chapter-indexed Arabic book data suitable for downstream tasks such as semantic search, question answering, and language model training. We contribute both the processing toolkit and the resulting corpus to the research community.

Future work includes: (1) expanding the corpus with additional open-source Arabic books across diverse genres and historical periods, (2) formal evaluation of TOC generation quality with annotated ground truth, (3) systematic confidence threshold analysis for language detection on book-length documents, (4) integration of semantic search using multilingual embeddings to enable cross-lingual question answering over the corpus, and (5) extension to additional RTL languages.

## References

[To be completed]

---

*Note: This paper follows LREC 2026 formatting guidelines for OSACT7 submission. The submission deadline is February 25, 2026.*