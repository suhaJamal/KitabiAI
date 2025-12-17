# app/routers/upload.py
"""
HTTP routes for the upload & analyze flow (unified English & Arabic support).

- GET "/" renders the upload form (HTML shell).
- POST "/upload" validates PDF, analyzes content, detects language, saves to database, and returns JSON/HTML.
- GET "/export/jsonl" streams page-level JSONL.
- GET "/export/sections.jsonl" streams sections from unified TOC extraction (bookmarks or pattern-based).
- GET "/info" returns metadata about last uploaded PDF (language, classification, etc.).
"""

import logging
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from ..ui.template import html_shell, render_home, render_report
from ..services.pdf_analyzer import PdfAnalyzer
from ..services.export_service import ExportService
from ..services.toc_extractor import TocExtractor
from ..services.language_detector import LanguageDetector
from ..models.schemas import AnalysisReport, BookMetadata, BookInfo, SectionsReport
from ..models.database import SessionLocal, Book, Section
from ..models.database import SessionLocal, Book, Section, Author, Category
from typing import Optional
import re

logger = logging.getLogger(__name__)
router = APIRouter()

# Services
analyzer = PdfAnalyzer()
exporter = ExportService()
toc_extractor = TocExtractor()
language_detector = LanguageDetector()

# In-memory state of last successful analysis
_last_report: Optional[AnalysisReport] = None
_last_filename: Optional[str] = None
_last_pdf_bytes: Optional[bytes] = None
_last_language: Optional[str] = None
_last_extracted_text: Optional[str] = None
_last_book_metadata: Optional[BookMetadata] = None
_last_sections_report: Optional[SectionsReport] = None  # Cache TOC extraction to avoid re-extraction
_last_book_id: Optional[int] = None # Track last inserted book ID

def create_slug(text: str) -> str:
    """
    Create URL-friendly slug from text.
    Example: "محمد عبده" -> "muhammad-abduh"
             "Bertrand Russell" -> "bertrand-russell"
    """
    if not text:
        return ""
    
    # Basic transliteration for Arabic (simplified)
    # For production, use a proper library like `arabic-reshaper` or `python-slugify`
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)  # Remove special chars
    text = re.sub(r'[\s_]+', '-', text)   # Replace spaces with hyphens
    text = text.strip('-')
    return text

@router.get("/", response_class=HTMLResponse)
def home():
    """Render the upload form with metadata fields."""
    return html_shell(render_home())


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    book_title: str = Form(...),  # Required
    author: str = Form(...),  
    author_slug: str = Form(None), #  Optional - for clean URLs
    enable_seo: bool = Form(False),  # Optional - SEO toggle
    description: str = Form(None),  # Optional - SEO
    category: str = Form(None),  # Optional - SEO
    keywords: str = Form(None),  # Optional - SEO
    publication_date: str = Form(None),  # Optional - SEO/Cataloging
    isbn: str = Form(None),  # Optional - SEO/Cataloging
    json: int = Query(default=0, ge=0, le=1)
):
    """
    Upload and analyze a PDF (English or Arabic) with user-provided metadata.

    Form fields:
        file: PDF file to analyze
        book_title: Book title (required)
        author: Author name (optional)
        author_slug: URL-friendly author name (optional, auto-generated if not provided)
        enable_seo: Enable SEO optimization (optional, default False)
        description: Brief book description for SEO (optional, max 160 chars)
        category: Book category/subject (optional)
        keywords: Comma-separated keywords/tags (optional)
        publication_date: Publication date (optional)
        isbn: ISBN number (optional)

    Query params:
        json: If 1, return JSON response. Otherwise, return HTML.
    """
    global _last_report, _last_filename, _last_pdf_bytes, _last_language
    global _last_extracted_text, _last_book_metadata, _last_sections_report, _last_book_id

    # Create and validate metadata object
    metadata = BookMetadata(
        title=book_title.strip(),
        author=author.strip() if author else None,
        enable_seo=enable_seo,
        description=description.strip() if description else None,
        category=category.strip() if category else None,
        keywords=keywords.strip() if keywords else None,
        publication_date=publication_date.strip() if publication_date else None,
        isbn=isbn.strip() if isbn else None
    )
    
    logger.info(f"Upload request - Book: '{metadata.title}', File: {file.filename}")
    
    # Validate PDF signature
    head = await file.read(5)
    await file.seek(0)
    analyzer.validate_signature(head)

    # Read PDF bytes
    pdf_bytes = await file.read()

    # Detect language and extract text FIRST (returns 2 values: language and extracted_text)
    detected_language, extracted_text = language_detector.detect(pdf_bytes)
    logger.info(f"Detected language: {detected_language}")

    # Analyze PDF with pre-extracted text (for Arabic) to maintain quality
    report = analyzer.analyze(pdf_bytes, extracted_text, detected_language)

    # Extract TOC sections immediately (to cache and avoid re-extraction during generation)
    logger.info(f"Extracting TOC for {detected_language} PDF during upload")
    if detected_language == "arabic" and extracted_text:
        from ..services.arabic_toc_extractor import ArabicTocExtractor
        arabic_extractor = ArabicTocExtractor()
        sections_report = arabic_extractor.extract(extracted_text)

        # Fix page ranges based on actual PDF page count
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for section in sections_report.sections:
            if section.page_end > doc.page_count or section.page_end == 9999:
                section.page_end = doc.page_count
        doc.close()
        logger.info(f"Arabic extraction result: {len(sections_report.sections)} sections")
    else:
        # For English (or if no cached text), use unified extractor
        sections_report = toc_extractor.extract(pdf_bytes)
        logger.info(f"English extraction result: {len(sections_report.sections)} sections")

    # Save to database
    db = SessionLocal()
    try:
        # 1. Handle Author (get existing or create new)
        author_obj = None
        if metadata.author:
            # Check if author exists
            author_obj = db.query(Author).filter(Author.name == metadata.author).first()
            
            if not author_obj:
                # Create new author
                author_slug = create_slug(metadata.author)
                author_obj = Author(
                    name=metadata.author,
                    slug=author_slug
                )
                db.add(author_obj)
                db.flush()  # Get the author ID
                logger.info(f"Created new author: {metadata.author} (ID: {author_obj.id})")
            else:
                logger.info(f"Using existing author: {metadata.author} (ID: {author_obj.id})")
        
        if not author_obj:
            raise HTTPException(status_code=400, detail="Author is required")
        
        # 2. Handle Category (get existing or create new)
        category_obj = None
        if metadata.category:
            # Check if category exists
            category_obj = db.query(Category).filter(Category.name == metadata.category).first()
            
            if not category_obj:
                # Create new category
                category_slug = create_slug(metadata.category)
                category_obj = Category(
                    name=metadata.category,
                    slug=category_slug
                )
                db.add(category_obj)
                db.flush()  # Get the category ID
                logger.info(f"Created new category: {metadata.category} (ID: {category_obj.id})")
            else:
                logger.info(f"Using existing category: {metadata.category} (ID: {category_obj.id})")
        
        # 3. Create book record with foreign keys
        new_book = Book(
            title=metadata.title,
            author_id=author_obj.id,  # CHANGED: Use foreign key
            category_id=category_obj.id if category_obj else None,  # CHANGED: Use foreign key
            language="ar" if detected_language == "arabic" else "en",
            description=metadata.description,
            keywords=metadata.keywords,
            publication_date=metadata.publication_date,
            isbn=metadata.isbn,
            page_count=report.num_pages,
            section_count=len(sections_report.sections),
            status='published'
        )
        
        db.add(new_book)
        db.flush()  # Get the book ID
        
        logger.info(f"Book saved to database with ID: {new_book.id}")
        
        # 4. Save sections (unchanged)
        for idx, section in enumerate(sections_report.sections):
            new_section = Section(
                book_id=new_book.id,
                title=section.title,
                level=section.level,
                page_start=section.page_start,
                page_end=section.page_end,
                order_index=idx
            )
            db.add(new_section)
        
        db.commit()
        logger.info(f"Saved {len(sections_report.sections)} sections to database")
        
        # Store book ID for later use
        _last_book_id = new_book.id
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")
    finally:
        db.close()

    # Cache for follow-up exports (including extracted text for BOTH languages)
    _last_report = report
    _last_filename = file.filename
    _last_pdf_bytes = pdf_bytes
    _last_language = detected_language
    _last_extracted_text = extracted_text  # Cache for both English and Arabic
    _last_book_metadata = metadata
    _last_sections_report = sections_report  # Cache TOC sections to avoid re-extraction
    
    # Return JSON or HTML
    if json == 1:
        return JSONResponse({
            "ok": True,
            "message": "Valid PDF uploaded and analyzed.",
            "book_id": _last_book_id,
            "metadata": metadata.model_dump(),
            "language": detected_language,
            "classification": report.classification,
            "num_pages": report.num_pages,
            "pages": [p.model_dump() for p in report.pages],
        })
    
    return HTMLResponse(
        html_shell(render_report(file.filename, report, detected_language, metadata))
    )


@router.get("/info")
def get_info():
    """
    Get complete book information including metadata and analysis results.
    
    Returns:
        BookInfo: Complete book information with metadata
    """
    if _last_report is None or _last_filename is None or _last_book_metadata is None:
        raise HTTPException(
            status_code=409,
            detail="No analysis available. Upload a PDF first."
        )
    
    book_info = BookInfo(
        metadata=_last_book_metadata,
        language=_last_language,
        classification=_last_report.classification,
        num_pages=_last_report.num_pages,
        filename=_last_filename,
        uploaded_at=datetime.utcnow().isoformat()
    )
    
    return JSONResponse(book_info.model_dump())


@router.get("/export/jsonl")
def export_jsonl():
    """
    Export page-level analysis as JSONL.
    Each line contains: page, has_text, image_count, text.
    """
    if _last_report is None or _last_filename is None:
        raise HTTPException(
            status_code=409,
            detail="No analysis available. Upload a PDF first."
        )
    
    data = exporter.to_jsonl(_last_report, include_text=True)
    fname = _last_filename.rsplit(".", 1)[0] + "_pages.jsonl"
    
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


@router.get("/export/sections.jsonl")
def export_sections_jsonl():
    """
    Export sections/TOC as JSONL with book metadata.

    First line: Book metadata object
    Following lines: Section objects

    Uses cached TOC sections from upload to avoid re-extraction.
    """
    global _last_sections_report

    if _last_pdf_bytes is None or _last_filename is None or _last_book_metadata is None:
        raise HTTPException(
            status_code=409,
            detail="No PDF in memory. Upload a PDF first."
        )

    if _last_sections_report is None:
        raise HTTPException(
            status_code=409,
            detail="No TOC sections available. Re-upload the PDF."
        )

    # Use cached sections (already extracted during upload)
    logger.info(f"Using cached TOC sections for {_last_language} PDF: {_last_filename}")
    sections_report = _last_sections_report
    
    # Convert to JSONL with metadata
    import json
    lines = []
    
    # First line: metadata
    metadata_line = {
        "type": "metadata",
        "book_id": _last_book_id,
        "book_title": _last_book_metadata.title,
        "author": _last_book_metadata.author,
        "publication_date": _last_book_metadata.publication_date,
        "isbn": _last_book_metadata.isbn,
        "language": _last_language,
        "num_pages": _last_report.num_pages,
        "filename": _last_filename,
        "exported_at": datetime.utcnow().isoformat()
    }
    lines.append(json.dumps(metadata_line, ensure_ascii=False))
    
    # Following lines: sections
    for s in sections_report.sections:
        section_line = {
            "type": "section",
            "section_id": s.section_id,
            "title": s.title,
            "level": s.level,
            "page_start": s.page_start,
            "page_end": s.page_end,
        }
        lines.append(json.dumps(section_line, ensure_ascii=False))
    
    data = ("\n".join(lines) + "\n").encode("utf-8")
    
    fname = _last_filename.rsplit(".", 1)[0] + "_sections.jsonl"
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )