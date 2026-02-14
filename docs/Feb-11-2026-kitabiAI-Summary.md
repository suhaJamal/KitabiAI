# KitabiAI Project Summary
**Date: February 11, 2026**
**Author: Suha Islaih**

---

## 1. Project Overview

**KitabiAI** is an intelligent Arabic and English book digitization platform that automatically processes PDF books into structured, accessible digital formats. The system combines Azure cloud services, machine learning, and sophisticated document processing to extract content, detect language, generate table of contents, and create multiple output formats (HTML, Markdown, JSONL).

**Live Platform**: https://kitabiai.azurewebsites.net/library

---

## 2. Technologies & Architecture

### Backend Stack
| Technology | Purpose |
|---|---|
| **FastAPI (Python)** | RESTful API framework |
| **SQLAlchemy + PostgreSQL** | Database ORM and Azure-hosted persistent storage |
| **Azure Document Intelligence** | Advanced OCR for Arabic text extraction |
| **FastText (176-language model)** | ML-based language detection |
| **PyMuPDF (fitz)** | PDF parsing and English text extraction |
| **Azure Blob Storage** | Cloud file storage (PDF, HTML, Markdown, images) |

### Frontend
- Vanilla JavaScript, HTML5, CSS3
- Full RTL (Right-to-Left) support for Arabic
- Dark mode with localStorage persistence
- Responsive design for mobile and desktop

### Infrastructure
- **Azure App Service** for hosting
- **Azure PostgreSQL** for database
- **GitHub Actions** for CI/CD
- **Docker** for containerization

### Service Architecture

```
app/
  services/
    language_detector.py       # FastText + Azure hybrid detection
    toc_extractor.py           # Extract TOC from book pages
    toc_generator.py           # Generate TOC from heading detection (NEW)
    arabic_toc_extractor.py    # Arabic-specific TOC extraction
    html_generator.py          # Responsive HTML with RTL support
    markdown_generator.py      # Markdown with proper headings
    chunker_service.py         # Semantic chunking for search
    ocr_detector.py            # Scanned vs. digital PDF detection
    pdf_analyzer.py            # PDF structure analysis
    azure_storage_service.py   # Azure Blob Storage management
  routers/
    upload.py                  # PDF upload and processing pipeline
    generation.py              # HTML/Markdown/JSONL generation
    library.py                 # Book browsing with search/filtering
    admin.py                   # Book management dashboard (NEW)
  models/
    database.py                # SQLAlchemy models (5 tables)
    schemas.py                 # Pydantic validation schemas
```

---

## 3. Development Phases

### Phase 1-3: Core Processing Pipeline
- Built foundational book processing architecture
- Implemented hybrid language detection (FastText + Azure OCR)
- Created database schema for books, authors, categories, pages, sections
- Deployed to Azure App Service with CI/CD pipeline

### Phase 4: Database-Backed Persistent Storage
- Added `pages` table to store extracted text per page
- Eliminated in-memory state dependency
- Enabled multi-worker safe operations on Azure
- Allowed incremental content regeneration without re-extraction

### Phase 5 (Current): Library UI, Admin & TOC Generator
- **Library Browsing Page**: Public interface with filtering, search, dark mode
- **Admin Management Page**: Book metadata editing, deletion, and management
- **TOC Generator**: New module to auto-detect section headings from document structure
- **API Endpoints** for books, authors, categories with pagination and statistics

---

## 4. Key Features

### 4.1 Intelligent Language Detection (Cost-Optimized)
**Two-Phase Extraction Architecture:**
- **Phase 1**: Sample pages 4-13 (skip cover) using PyMuPDF + FastText (free)
- **Phase 2**: Full extraction routed by language - Azure for Arabic, PyMuPDF for English
- **Result**: 96% detection accuracy with 82% cost reduction

### 4.2 Automatic Table of Contents

**Method 1 - Extract from Book:**
- Bookmark-based extraction for PDFs with embedded bookmarks
- Table-based extraction using Azure Document Intelligence for Arabic books
- Pattern-based extraction for English books

**Method 2 - Generate from Headings (NEW):**
- Auto-detect section titles using Azure's paragraph role detection
- Uses `title` and `sectionHeading` roles from Azure Document Intelligence
- Solves page offset problem by using actual PDF page numbers
- Best for books without formal TOC pages or old scanned books

### 4.3 Multi-Format Output Generation
- **HTML**: Responsive design with full RTL support for Arabic
- **Markdown**: Proper heading hierarchy (H1-H3)
- **JSONL**: Page-level and section-level data for search indexing

### 4.4 Scanned vs. Digital PDF Detection
- Text density analysis (100 chars/page threshold)
- 95% detection accuracy on 80-book test corpus
- Prevents unnecessary Azure OCR costs for digital PDFs

### 4.5 Library Browsing System
- RTL interface for Arabic content
- Real-time statistics dashboard
- Dynamic filtering (language, author, category)
- Full-text search with debouncing
- Dark mode toggle
- Responsive grid layout with book cards and cover images

### 4.6 Admin Management Dashboard (NEW)
- Browse all books with metadata summary
- Edit book information (title, author, description, category, keywords, ISBN)
- Delete books with cascading cleanup of sections and pages
- Statistics overview (total books, Arabic/English counts, total pages)

---

## 5. Challenges & Solutions

### Challenge 1: Cost vs. Accuracy Trade-off
**Problem**: Azure OCR costs ~$0.15/book; PyMuPDF is free but only 60% accurate for Arabic.

**Solution**: Two-phase sampling architecture - use free tools for language detection, then route to the appropriate extraction method.

**Result**: 82% cost reduction while maintaining 96% extraction accuracy.

### Challenge 2: Arabic RTL Text Preservation
**Problem**: PyMuPDF extracts RTL text in visual order, breaking logical reading order.

**Solution**: Use Azure's line-by-line extraction with form feed page boundaries for Arabic content.

**Result**: 96% accuracy preserving diacritics and reading order.

### Challenge 3: 10-Page Extraction Bug
**Problem**: Initial implementation returned only a 10-page sample instead of full text.

**Root Cause**: Phase 2 (full extraction) was not implemented after language detection sampling.

**Fix**: Implemented proper two-phase workflow with correct state management. All pages now stored in database.

### Challenge 4: TOC Page Offset Problem
**Problem**: Book page numbers don't match PDF page numbers (e.g., book page 1 = PDF page 15).

**Solution (Partial)**: User-provided page offset parameter in upload form.

**Solution (New)**: TOC Generator approach - detects headings throughout the document using actual PDF page numbers, completely bypassing the offset problem.

### Challenge 5: Industry Standard Parameters Don't Transfer
**Problem**: 70% FastText confidence threshold (industry standard) underperformed for book content.

**Discovery**: Book content has different language statistics than web training data.

**Solution**: Domain-specific calibration to 90% threshold, achieving 95% routing accuracy.

### Challenge 6: Gibberish Detection
**Problem**: Distinguishing OCR errors from valid text.

**Solution**: Monitor for unexpected language codes - if FastText detects French/Urdu in an Arabic book, the extraction quality is suspect.

**Result**: 95% gibberish detection accuracy.

### Challenge 7: Multi-Worker Database Consistency
**Problem**: In-memory state lost on server restart, race conditions with multiple workers.

**Solution**: Phase 4 database-backed page storage with row-level granularity.

**Result**: Content survives restarts, multi-worker safe, enables regeneration without re-extraction.

### Challenge 8: Small Text Detected as Headings (TOC Generator)
**Problem**: Azure detected small inline text as section headings during TOC generation.

**Solution**: Bounding box height filtering - paragraphs with bounding box height below threshold (0.025) are filtered out. Also filtering purely numeric content (page numbers) and numbered paragraphs that aren't chapter titles.

---

## 6. Database Architecture

```
books (24 records)
  |-- id, title, title_ar, language (ar/en)
  |-- author_id --> authors (6 records)
  |-- category_id --> categories (14 records)
  |-- page_count, section_count
  |-- html_url, markdown_url, pdf_url, cover_image_url
  |-- view_count, status, created_at, updated_at
  |
  |-- pages (4,185+ records)
  |     |-- page_number, text, word_count, char_count, has_images
  |
  |-- sections (750+ records)
        |-- title, level (1-3), page_start, page_end
        |-- content, order_index
```

---

## 7. Key Metrics

| Metric | Value |
|---|---|
| Total Development Time | ~225 hours |
| API Endpoints | 12+ active |
| Database Tables | 5 |
| Supported Languages | 2 (Arabic, English) |
| Language Detection Model | 176 languages |
| Cost Reduction | 82% vs. baseline |
| Extraction Accuracy | 96% (Arabic), 95% (English) |
| Language Detection Accuracy | 96% |
| Scanned PDF Detection | 95% |
| Books Processed | 24 |
| Total Pages Digitized | 4,185+ |

---

## 8. What's Next

### Phase 6: Bilingual AI Chatbot
- Semantic search using embeddings (multilingual-e5, Arabic-BERT)
- Cross-lingual Q&A (ask in English about Arabic books and vice versa)
- Citation accuracy with hallucination prevention
- Cost optimization for LLM context windows

### Improvements to TOC
- Page offset auto-detection via OCR of page numbers
- Content-section alignment validation with fuzzy matching
- Confidence scoring for section boundaries

### Operational Enhancements
- Batch upload processing with queue-based architecture
- Progress indicators via WebSocket
- Manual section editor for overriding auto-detected sections

---

## 9. Technical Innovations (SR&ED Research)

1. **Cost-Optimized Hybrid Extraction**: Combined free and paid OCR services with intelligent routing
2. **Domain-Specific ML Calibration**: Discovered industry-standard thresholds don't work for book content
3. **Quality Detection via Language Codes**: Novel approach using language detection for gibberish identification
4. **Page-Boundary Preservation**: Form feed characters maintain logical reading order in RTL text
5. **Heading-Based TOC Generation**: Using Azure paragraph role detection as alternative to traditional TOC extraction
6. **Text Density Scanned Detection**: Empirically determined optimal threshold for scanned PDF identification

---

## 10. Project Status

| Component | Status |
|---|---|
| Core Processing Pipeline | Complete |
| Language Detection | Complete |
| TOC Extraction | Complete |
| TOC Generation (from headings) | Complete (New) |
| HTML/Markdown Generation | Complete |
| Database Persistence | Complete |
| Library Browsing UI | Complete |
| Admin Management Dashboard | Complete (New) |
| Azure Deployment | Complete |
| CI/CD Pipeline | Automated |
| AI Chatbot | Planned (Phase 6) |
| Batch Processing | Planned |

---

*Document generated on February 11, 2026*
*KitabiAI - Intelligent Arabic & English Book Digitization Platform*