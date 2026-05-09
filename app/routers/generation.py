# app/routers/generation.py
"""
HTTP routes for content generation (Markdown & HTML).

New endpoints:
- POST /generate/markdown - Generate and download Markdown file
- POST /generate/html - Generate and download HTML file
- GET /generate/chunks - Get chunked data (JSON)
"""


import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from ..services.generation.chunker_service import ChunkerService
from ..services.generation.markdown_generator import MarkdownGenerator
from ..services.generation.html_generator import HtmlGenerator
from ..services.storage.azure_storage_service import azure_storage
from ..models.schemas import GenerationRequest, GenerationResponse
from ..models.database import SessionLocal, Book

router = APIRouter(prefix="/generate", tags=["generation"])

# Services
chunker = ChunkerService()
md_generator = MarkdownGenerator()
html_generator = HtmlGenerator()

# Import state from upload router (we'll need to refactor this later)
# For now, assuming we have access to the same in-memory state
from .upload import (
    _last_report,
    _last_filename,
    _last_pdf_bytes,
    _last_language,
    _last_extracted_text,
    _last_book_metadata,
    _last_sections_report,
    _last_book_id
)


def _check_state():
    """Check if we have required state from upload (tries in-memory first, then database)."""
    from .upload import _last_report, _last_book_metadata, _last_sections_report, _last_book_id

    # First try in-memory state (fast path for immediate generation after upload)
    if _last_report is not None and _last_book_metadata is not None and _last_sections_report is not None and _last_book_id is not None:
        return  # All good, use in-memory state

    # If in-memory state is missing, we need to load from database
    # This happens after server restart or with multiple workers
    # For now, raise an error - we'll implement database loading in the generation function
    if _last_book_id is None:
        raise HTTPException(
            status_code=409,
            detail="No analysis available. Upload a PDF first."
        )


def _generate_pages_jsonl() -> str:
    """Generate pages JSONL content (page-level analysis)."""
    from .upload import _last_report
    from ..services.generation.export_service import ExportService

    exporter = ExportService()
    # ExportService returns bytes, we need to decode to string
    jsonl_bytes = exporter.to_jsonl(_last_report, include_text=True)
    return jsonl_bytes.decode('utf-8')


def _generate_sections_jsonl() -> str:
    """Generate sections JSONL content (TOC sections with metadata)."""
    from .upload import (
        _last_sections_report, _last_book_id, _last_book_metadata,
        _last_language, _last_report, _last_filename
    )

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
    for s in _last_sections_report.sections:
        section_line = {
            "type": "section",
            "section_id": s.section_id,
            "title": s.title,
            "level": s.level,
            "page_start": s.page_start,
            "page_end": s.page_end,
        }
        lines.append(json.dumps(section_line, ensure_ascii=False))

    return "\n".join(lines) + "\n"


def _update_book_urls(
    book_id: int,
    html_url: str = None,
    markdown_url: str = None,
    pages_jsonl_url: str = None,
    sections_jsonl_url: str = None
):
    """
    Update book record with file URLs and generation timestamp.

    Args:
        book_id: Database book ID
        html_url: URL to HTML file
        markdown_url: URL to Markdown file
        pages_jsonl_url: URL to pages JSONL file
        sections_jsonl_url: URL to sections JSONL file
    """
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

        # Update URLs (only if provided)
        if html_url:
            book.html_url = html_url
        if markdown_url:
            book.markdown_url = markdown_url
        if pages_jsonl_url:
            book.pages_jsonl_url = pages_jsonl_url
        if sections_jsonl_url:
            book.sections_jsonl_url = sections_jsonl_url

        # Update generation timestamp
        book.files_generated_at = datetime.utcnow()

        db.commit()
        db.refresh(book)

    finally:
        db.close()


@router.post("/markdown")
async def generate_markdown(
    include_toc: bool = Query(True, description="Include table of contents"),
    include_metadata: bool = Query(True, description="Include frontmatter metadata"),
    chunk_size: int = Query(None, description="Words per chunk (None = section-based)")
):
    """
    Generate Markdown file from uploaded PDF and trigger download.

    Query params:
        include_toc: Include table of contents
        include_metadata: Include YAML frontmatter
        chunk_size: Split sections larger than this (None = keep sections intact)
    """
    _check_state()

    from .upload import (
        _last_report, _last_filename,
        _last_language, _last_book_metadata, _last_sections_report
    )

    # Use cached TOC sections (already extracted during upload)
    sections_report = _last_sections_report

    # Generate Markdown
    markdown_content = md_generator.generate(
        metadata=_last_book_metadata,
        sections=sections_report.sections,
        pages=_last_report.pages,
        language=_last_language,
        include_toc=include_toc,
        include_metadata=include_metadata
    )

    # Return file for download (no local save needed - Phase 3 uses Azure Blob Storage)
    base_name = _last_filename.rsplit(".", 1)[0]
    output_filename = f"{base_name}.md"

    # Return file for download
    from fastapi.responses import Response
    return Response(
        content=markdown_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"'
        }
    )


@router.post("/html")
async def generate_html(
    include_toc: bool = Query(True, description="Include navigation sidebar"),
):
    """
    Generate HTML file from uploaded PDF and display in browser.

    Query params:
        include_toc: Include navigation sidebar with table of contents
    """
    _check_state()

    from .upload import (
        _last_report, _last_filename,
        _last_language, _last_book_metadata, _last_sections_report
    )
    from fastapi.responses import HTMLResponse

    # Use cached TOC sections (already extracted during upload)
    sections_report = _last_sections_report

    # Generate HTML
    html_content = html_generator.generate(
        metadata=_last_book_metadata,
        sections=sections_report.sections,
        pages=_last_report.pages,
        language=_last_language,
        include_toc=include_toc
    )

    # Return HTML directly - will open in same tab (no local save needed - Phase 3 uses Azure Blob Storage)
    return HTMLResponse(content=html_content)


@router.get("/chunks")
async def get_chunks(
    strategy: str = Query("smart", description="Chunking strategy: smart, sections, or pages"),
    max_words: int = Query(2000, description="Maximum words per chunk"),
):
    """
    Get chunked data as JSON.
    
    Query params:
        strategy: Chunking strategy (smart, sections, pages)
        max_words: Maximum words per chunk
    """
    _check_state()

    from .upload import _last_report, _last_sections_report

    # Use cached TOC sections (already extracted during upload)
    sections_report = _last_sections_report

    # Chunk based on strategy
    chunker_svc = ChunkerService(max_words=max_words)
    
    if strategy == "sections":
        chunking_report = chunker_svc.chunk_by_sections(
            sections_report.sections,
            _last_report.pages,
            split_large=True
        )
    elif strategy == "pages":
        chunking_report = chunker_svc.chunk_by_pages(
            _last_report.pages,
            pages_per_chunk=5
        )
    else:  # smart
        chunking_report = chunker_svc.smart_chunk(
            sections_report.sections,
            _last_report.pages,
            _last_report
        )
    
    return JSONResponse(chunking_report.model_dump())


@router.post("/both")
async def generate_both(
    include_toc: bool = Query(True, description="Include table of contents"),
    include_metadata: bool = Query(True, description="Include metadata"),
    book_id: int = Query(None, description="Generate for a specific book ID (loads from database)"),
):
    """
    Generate both Markdown and HTML files, plus JSONL exports.
    Saves files to Azure Blob Storage and updates database with file URLs.

    Pass book_id to generate for a book whose in-memory state was lost
    (e.g. after a timeout or server restart) — all data is loaded from the database.

    Returns URLs for all generated files.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from .upload import (
            _last_report, _last_filename,
            _last_language, _last_book_metadata, _last_sections_report,
            _last_book_id
        )
        from ..models.database import SessionLocal, Book, Section, Page, Author
        from ..models.schemas import PageInfo, BookMetadata, SectionInfo, SectionsReport, AnalysisReport

        # Resolve which book to generate for
        target_book_id = book_id or _last_book_id

        # Determine whether to load from DB
        use_memory = (
            book_id is None and
            _last_report is not None and
            _last_book_metadata is not None and
            _last_sections_report is not None and
            _last_book_id is not None
        )

        if not use_memory and target_book_id is None:
            raise HTTPException(
                status_code=409,
                detail="No book to generate. Pass book_id= or upload a PDF first."
            )

        logger.info(f"Starting generation for book_id={target_book_id} (source={'memory' if use_memory else 'database'})")

        db = SessionLocal()
        try:
            if use_memory:
                # Fast path: use in-memory state from upload
                db_pages = db.query(Page).filter(Page.book_id == target_book_id).order_by(Page.page_number).all()
                if not db_pages:
                    raise HTTPException(status_code=404, detail=f"No pages found for book_id={target_book_id}")

                pages = [
                    PageInfo(
                        page=p.page_number,
                        text=p.text or "",
                        has_text=bool(p.text and len(p.text.strip()) > 0),
                        image_count=p.has_images or 0
                    )
                    for p in db_pages
                ]
                report = AnalysisReport(num_pages=len(pages), pages=pages, classification="mixed")
                sections_report = _last_sections_report
                base_name = _last_filename.rsplit(".", 1)[0]
                metadata = _last_book_metadata
                language = _last_language

            else:
                # DB path: load everything from database (used when in-memory state is gone)
                book = db.query(Book).filter(Book.id == target_book_id).first()
                if not book:
                    raise HTTPException(status_code=404, detail=f"Book {target_book_id} not found")

                author = db.query(Author).filter(Author.id == book.author_id).first()

                db_pages = db.query(Page).filter(Page.book_id == target_book_id).order_by(Page.page_number).all()
                if not db_pages:
                    raise HTTPException(status_code=404, detail=f"No pages found for book_id={target_book_id}")

                db_sections = db.query(Section).filter(Section.book_id == target_book_id).order_by(Section.order_index).all()
                if not db_sections:
                    raise HTTPException(status_code=404, detail=f"No sections found for book_id={target_book_id}")

                logger.info(f"Loaded from DB: {len(db_pages)} pages, {len(db_sections)} sections")

                pages = [
                    PageInfo(
                        page=p.page_number,
                        text=p.text or "",
                        has_text=bool(p.text and len(p.text.strip()) > 0),
                        image_count=p.has_images or 0
                    )
                    for p in db_pages
                ]
                report = AnalysisReport(num_pages=len(pages), pages=pages, classification="mixed")

                section_infos = [
                    SectionInfo(
                        section_id=str(s.order_index + 1),
                        title=s.title,
                        level=s.level,
                        page_start=s.page_start,
                        page_end=s.page_end,
                        content=s.content or None
                    )
                    for s in db_sections
                ]
                sections_report = SectionsReport(bookmarks_found=True, sections=section_infos)

                metadata = BookMetadata(
                    title=book.title,
                    author=author.name if author else None,
                    description=book.description,
                    keywords=book.keywords,
                    publication_date=book.publication_date,
                    isbn=book.isbn
                )
                language = "arabic" if book.language == "ar" else "english"
                base_name = book.title[:50].replace(" ", "_")

        finally:
            db.close()

        # Generate Markdown
        logger.info("Generating Markdown...")
        markdown_content = md_generator.generate(
            metadata=metadata,
            sections=sections_report.sections,
            pages=report.pages,
            language=language,
            include_toc=include_toc,
            include_metadata=include_metadata
        )
        logger.info(f"Markdown generated: {len(markdown_content)} chars")

        # Generate HTML
        logger.info("Generating HTML...")
        html_content = html_generator.generate(
            metadata=metadata,
            sections=sections_report.sections,
            pages=report.pages,
            language=language,
            include_toc=include_toc
        )
        logger.info(f"HTML generated: {len(html_content)} chars")

        # Generate JSONL files
        logger.info("Generating JSONL files...")

        # Generate pages JSONL using the loaded report
        from ..services.generation.export_service import ExportService
        exporter = ExportService()
        jsonl_bytes = exporter.to_jsonl(report, include_text=True)
        pages_jsonl_content = jsonl_bytes.decode('utf-8')

        sections_jsonl_content = _generate_sections_jsonl()
        logger.info(f"JSONL generated: pages={len(pages_jsonl_content)} chars, sections={len(sections_jsonl_content)} chars")

        # Save all files to Azure Blob Storage and get URLs
        logger.info("Uploading to Azure Blob Storage...")
        html_url = azure_storage.save_html(target_book_id, html_content, f"{base_name}.html")
        logger.info(f"HTML uploaded: {html_url}")

        markdown_url = azure_storage.save_markdown(target_book_id, markdown_content, f"{base_name}.md")
        logger.info(f"Markdown uploaded: {markdown_url}")

        pages_jsonl_url = azure_storage.save_pages_jsonl(target_book_id, pages_jsonl_content, f"{base_name}_pages.jsonl")
        logger.info(f"Pages JSONL uploaded: {pages_jsonl_url}")

        sections_jsonl_url = azure_storage.save_sections_jsonl(target_book_id, sections_jsonl_content, f"{base_name}_sections.jsonl")
        logger.info(f"Sections JSONL uploaded: {sections_jsonl_url}")

        # Update database with URLs and timestamp
        logger.info("Updating database...")
        _update_book_urls(
            book_id=target_book_id,
            html_url=html_url,
            markdown_url=markdown_url,
            pages_jsonl_url=pages_jsonl_url,
            sections_jsonl_url=sections_jsonl_url
        )
        logger.info("Database updated successfully")

        return JSONResponse({
            "ok": True,
            "message": "Generated all files and saved to Azure Blob Storage",
            "book_id": target_book_id,
            "files": [
                {
                    "format": "html",
                    "filename": f"{base_name}.html",
                    "size_bytes": len(html_content.encode('utf-8')),
                    "url": html_url
                },
                {
                    "format": "markdown",
                    "filename": f"{base_name}.md",
                    "size_bytes": len(markdown_content.encode('utf-8')),
                    "url": markdown_url
                },
                {
                    "format": "pages_jsonl",
                    "filename": f"{base_name}_pages.jsonl",
                    "size_bytes": len(pages_jsonl_content.encode('utf-8')),
                    "url": pages_jsonl_url
                },
                {
                    "format": "sections_jsonl",
                    "filename": f"{base_name}_sections.jsonl",
                    "size_bytes": len(sections_jsonl_content.encode('utf-8')),
                    "url": sections_jsonl_url
                }
            ],
            "sections_count": len(sections_report.sections),
            "files_generated_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate files: {str(e)}"
        )
