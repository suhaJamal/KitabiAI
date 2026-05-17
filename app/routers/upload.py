# app/routers/upload.py
"""
HTTP routes for the upload & analyze flow (unified English & Arabic support).

- GET "/" renders the upload form (HTML shell).
- POST "/upload" validates PDF, analyzes content, detects language, saves to database, and returns JSON/HTML.
- GET "/export/jsonl" streams page-level JSONL.
- GET "/export/sections.jsonl" streams sections from unified TOC extraction (bookmarks or pattern-based).
- GET "/info" returns metadata about last uploaded PDF (language, classification, etc.).

"""


import asyncio
import functools
import logging
import time
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from ..ui.template import html_shell, render_home, render_report
from ..services.extraction.pdf_analyzer import PdfAnalyzer
from ..services.generation.export_service import ExportService
from ..services.extraction.toc_extractor import TocExtractor
from ..services.detection.language_detector import LanguageDetector
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


def _process_upload_sync(
    pdf_bytes: bytes,
    cover_bytes: Optional[bytes],
    original_filename: str,
    cover_filename: Optional[str],
    metadata: BookMetadata,
    book_language: str,
    toc_method: str,
    toc_page_int: Optional[int],
    toc_page_end_int: Optional[int],
    page_offset: int,
    generate_skip_pages: int,
) -> dict:
    """All blocking I/O for upload: Azure DI, TOC extraction, DB save, blob storage."""
    detected_language = book_language
    t_azure_start = time.time()
    if detected_language == "arabic":
        extracted_text, azure_result = language_detector._extract_with_azure(pdf_bytes)
    else:
        extracted_text = language_detector._extract_full_with_pymupdf(pdf_bytes)
        azure_result = None
    logger.info(f"[TIMING] Azure/text extraction: {time.time() - t_azure_start:.1f}s | Language: {detected_language}")

    report = analyzer.analyze(pdf_bytes, extracted_text, detected_language)

    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    num_pages = doc.page_count

    if toc_method == "generate":
        logger.info(f"Generating TOC from headings for {detected_language} PDF")
        from ..services.extraction.toc_generator import TocGenerator
        toc_generator = TocGenerator()
        if azure_result:
            content_start_page = generate_skip_pages + 1 if generate_skip_pages > 0 else 1
            sections_report = toc_generator.generate(
                azure_result=azure_result,
                num_pages=num_pages,
                store_content=True,
                book_title=metadata.title,
                content_start_page=content_start_page
            )
            logger.info(f"Generated TOC with {len(sections_report.sections)} sections from headings")
        else:
            logger.warning("TOC generation requires Azure result. Falling back to extraction.")
            sections_report = toc_extractor.extract(pdf_bytes, book_title=metadata.title)
            logger.info(f"Fallback extraction result: {len(sections_report.sections)} sections")
    else:
        logger.info(f"Extracting TOC for {detected_language} PDF during upload")
        if detected_language == "arabic" and extracted_text:
            from ..services.extraction.arabic_toc_extractor import ArabicTocExtractor
            arabic_extractor = ArabicTocExtractor()
            t_toc_start = time.time()
            sections_report = arabic_extractor.extract(
                extracted_text,
                toc_page_number=toc_page_int,
                toc_page_end=toc_page_end_int,
                azure_result=azure_result,
                page_offset=page_offset,
                book_title=metadata.title
            )
            logger.info(f"[TIMING] TOC extraction: {time.time() - t_toc_start:.1f}s | {len(sections_report.sections)} sections")
            for section in sections_report.sections:
                if section.page_end > num_pages or section.page_end == 9999:
                    section.page_end = num_pages
            if azure_result:
                from ..services.extraction.toc_generator import TocGenerator
                toc_generator = TocGenerator()
                t_fill_start = time.time()
                toc_generator.fill_content_from_azure(sections_report.sections, azure_result)
                logger.info(f"[TIMING] fill_content_from_azure: {time.time() - t_fill_start:.1f}s")
            logger.info(f"Arabic extraction result: {len(sections_report.sections)} sections")
        else:
            sections_report = toc_extractor.extract(pdf_bytes, book_title=metadata.title)
            logger.info(f"English extraction result: {len(sections_report.sections)} sections")

    doc.close()

    # Save to database
    t_db_start = time.time()
    db = SessionLocal()
    existing_book = None
    book_id = None
    try:
        author_obj = None
        if metadata.author:
            author_obj = db.query(Author).filter(Author.name == metadata.author).first()
            if not author_obj:
                author_slug = create_slug(metadata.author)
                author_obj = Author(name=metadata.author, slug=author_slug)
                db.add(author_obj)
                db.flush()
                logger.info(f"Created new author: {metadata.author} (ID: {author_obj.id})")
            else:
                logger.info(f"Using existing author: {metadata.author} (ID: {author_obj.id})")

        if not author_obj:
            raise HTTPException(status_code=400, detail="Author is required")

        category_obj = None
        if metadata.category:
            category_obj = db.query(Category).filter(Category.name == metadata.category).first()
            if not category_obj:
                category_slug = create_slug(metadata.category)
                category_obj = Category(name=metadata.category, slug=category_slug)
                db.add(category_obj)
                db.flush()
                logger.info(f"Created new category: {metadata.category} (ID: {category_obj.id})")
            else:
                logger.info(f"Using existing category: {metadata.category} (ID: {category_obj.id})")

        stored_title = f"{metadata.title}-{toc_method}"

        existing_book = db.query(Book).filter(
            Book.title == stored_title,
            Book.author_id == author_obj.id
        ).first()

        if existing_book:
            logger.info(f"Book already exists with ID: {existing_book.id} - updating record")
            deleted_count = db.query(Section).filter(Section.book_id == existing_book.id).delete()
            logger.info(f"Deleted {deleted_count} old sections for book ID: {existing_book.id}")
            existing_book.language = "ar" if detected_language == "arabic" else "en"
            existing_book.page_count = report.num_pages
            existing_book.section_count = len(sections_report.sections)
            existing_book.description = metadata.description
            existing_book.keywords = metadata.keywords
            existing_book.publication_date = metadata.publication_date
            existing_book.isbn = metadata.isbn
            existing_book.category_id = category_obj.id if category_obj else None
            existing_book.status = 'published'
            book_id = existing_book.id
            logger.info(f"Updated existing book record with ID: {book_id}")
        else:
            new_book = Book(
                title=stored_title,
                author_id=author_obj.id,
                category_id=category_obj.id if category_obj else None,
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
            db.flush()
            book_id = new_book.id
            logger.info(f"Created new book with ID: {book_id}")

        for idx, section in enumerate(sections_report.sections):
            new_section = Section(
                book_id=book_id,
                title=section.title,
                level=section.level,
                page_start=section.page_start,
                page_end=section.page_end,
                content=section.content if section.content else None,
                order_index=idx
            )
            db.add(new_section)
        logger.info(f"Saved {len(sections_report.sections)} new sections to database")

        from ..models.database import Page
        if existing_book:
            deleted_pages = db.query(Page).filter(Page.book_id == book_id).delete()
            logger.info(f"Deleted {deleted_pages} old pages for book ID: {book_id}")

        for page in report.pages:
            page_text = page.text or ""
            word_count = len(page_text.split()) if page_text else 0
            new_page = Page(
                book_id=book_id,
                page_number=page.page,
                text=page_text,
                word_count=word_count,
                char_count=len(page_text),
                has_images=page.image_count if hasattr(page, 'image_count') else 0
            )
            db.add(new_page)

        db.commit()
        logger.info(f"[TIMING] DB save ({len(report.pages)} pages, {len(sections_report.sections)} sections): {time.time() - t_db_start:.1f}s")

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")
    finally:
        db.close()

    # Save PDF and cover image to Azure Blob Storage
    from ..services.storage.azure_storage_service import azure_storage

    t_blob_start = time.time()
    pdf_url = azure_storage.save_pdf(book_id, pdf_bytes, original_filename)
    logger.info(f"[TIMING] Blob PDF upload: {time.time() - t_blob_start:.1f}s | url: {pdf_url}")

    cover_url = None
    if cover_bytes:
        t_cover_start = time.time()
        cover_url = azure_storage.save_cover_image(book_id, cover_bytes, cover_filename)
        logger.info(f"[TIMING] Blob cover upload: {time.time() - t_cover_start:.1f}s")

    db2 = SessionLocal()
    try:
        book_record = db2.query(Book).filter(Book.id == book_id).first()
        if book_record:
            book_record.pdf_url = pdf_url
            if cover_url:
                book_record.cover_image_url = cover_url
            db2.commit()
            logger.info(f"Updated book {book_id} with PDF and cover URLs")
    finally:
        db2.close()

    return {
        "book_id": book_id,
        "report": report,
        "detected_language": detected_language,
        "extracted_text": extracted_text,
        "sections_report": sections_report,
    }


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    book_title: str = Form(...),
    author: str = Form(...),
    author_slug: str = Form(None),
    enable_seo: bool = Form(False),
    description: str = Form(None),
    category: str = Form(None),
    keywords: str = Form(None),
    publication_date: str = Form(None),
    isbn: str = Form(None),
    book_language: str = Form("arabic"),
    toc_method: str = Form("extract"),
    toc_page: str = Form(None),
    toc_page_end: str = Form(None),
    page_offset: int = Form(0),
    generate_skip_pages: int = Form(0),
    cover_image: UploadFile = File(None),
    json: int = Query(default=0, ge=0, le=1)
):
    global _last_report, _last_filename, _last_pdf_bytes, _last_language
    global _last_extracted_text, _last_book_metadata, _last_sections_report, _last_book_id

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

    toc_page_int = int(toc_page) if toc_page and toc_page.strip() else None
    toc_page_end_int = int(toc_page_end) if toc_page_end and toc_page_end.strip() else None

    logger.info(f"Upload request - Book: '{metadata.title}', File: {file.filename}")
    logger.info(f"TOC method: {toc_method}")
    if toc_method == "extract" and (toc_page_int or page_offset):
        logger.info(f"TOC extraction params - Page: {toc_page_int}, Offset: {page_offset}")

    # Async I/O: validate then read all file bytes before entering executor
    head = await file.read(5)
    await file.seek(0)
    analyzer.validate_signature(head)

    pdf_bytes = await file.read()
    cover_bytes = await cover_image.read() if cover_image else None

    # Run all blocking work (Azure DI, TOC, DB, blobs) in thread-pool so the event loop stays free
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        functools.partial(
            _process_upload_sync,
            pdf_bytes=pdf_bytes,
            cover_bytes=cover_bytes,
            original_filename=file.filename,
            cover_filename=cover_image.filename if cover_image else None,
            metadata=metadata,
            book_language=book_language,
            toc_method=toc_method,
            toc_page_int=toc_page_int,
            toc_page_end_int=toc_page_end_int,
            page_offset=page_offset,
            generate_skip_pages=generate_skip_pages,
        )
    )

    # Update in-memory cache for follow-up exports
    _last_book_id = result["book_id"]
    _last_report = result["report"]
    _last_language = result["detected_language"]
    _last_extracted_text = result["extracted_text"]
    _last_sections_report = result["sections_report"]
    _last_filename = file.filename
    _last_pdf_bytes = pdf_bytes
    _last_book_metadata = metadata

    if json == 1:
        return JSONResponse({
            "ok": True,
            "message": "Valid PDF uploaded and analyzed.",
            "book_id": _last_book_id,
            "metadata": metadata.model_dump(),
            "language": _last_language,
            "classification": _last_report.classification,
            "num_pages": _last_report.num_pages,
            "pages": [p.model_dump() for p in _last_report.pages],
        })

    return HTMLResponse(
        html_shell(render_report(file.filename, _last_report, _last_language, metadata))
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