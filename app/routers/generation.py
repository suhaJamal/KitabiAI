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

from ..services.chunker_service import ChunkerService
from ..services.markdown_generator import MarkdownGenerator
from ..services.html_generator import HtmlGenerator
from ..services.azure_storage_service import azure_storage
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


def _ensure_output_dir():
    """Ensure output directory exists."""
    output_dir = "/mnt/user-data/outputs"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _check_state():
    """Check if we have required state from upload."""
    from .upload import _last_report, _last_book_metadata, _last_sections_report, _last_book_id

    if _last_report is None or _last_book_metadata is None:
        raise HTTPException(
            status_code=409,
            detail="No analysis available. Upload a PDF first."
        )

    if _last_sections_report is None:
        raise HTTPException(
            status_code=409,
            detail="No TOC sections available. Re-upload the PDF."
        )

    if _last_book_id is None:
        raise HTTPException(
            status_code=409,
            detail="No book ID available. Re-upload the PDF."
        )


def _generate_pages_jsonl() -> str:
    """Generate pages JSONL content (page-level analysis)."""
    from .upload import _last_report
    from ..services.export_service import ExportService

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
    
    # Save to output directory
    output_dir = _ensure_output_dir()
    base_name = _last_filename.rsplit(".", 1)[0]
    output_filename = f"{base_name}.md"
    output_path = os.path.join(output_dir, output_filename)
    
    md_generator.save_to_file(markdown_content, output_path)
    
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
    
    # Save to output directory
    output_dir = _ensure_output_dir()
    base_name = _last_filename.rsplit(".", 1)[0]
    output_filename = f"{base_name}.html"
    output_path = os.path.join(output_dir, output_filename)
    
    html_generator.save_to_file(html_content, output_path)
    
    # Return HTML directly - will open in same tab
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
):
    """
    Generate both Markdown and HTML files, plus JSONL exports.
    Saves files locally and updates database with file URLs.

    Returns URLs for all generated files.
    """
    _check_state()

    from .upload import (
        _last_report, _last_filename,
        _last_language, _last_book_metadata, _last_sections_report,
        _last_book_id
    )

    # Use cached TOC sections (already extracted during upload)
    sections_report = _last_sections_report
    base_name = _last_filename.rsplit(".", 1)[0]

    # Generate Markdown
    markdown_content = md_generator.generate(
        metadata=_last_book_metadata,
        sections=sections_report.sections,
        pages=_last_report.pages,
        language=_last_language,
        include_toc=include_toc,
        include_metadata=include_metadata
    )

    # Generate HTML
    html_content = html_generator.generate(
        metadata=_last_book_metadata,
        sections=sections_report.sections,
        pages=_last_report.pages,
        language=_last_language,
        include_toc=include_toc
    )

    # Generate JSONL files
    pages_jsonl_content = _generate_pages_jsonl()
    sections_jsonl_content = _generate_sections_jsonl()

    # Save all files to Azure Blob Storage and get URLs
    html_url = azure_storage.save_html(_last_book_id, html_content, f"{base_name}.html")
    markdown_url = azure_storage.save_markdown(_last_book_id, markdown_content, f"{base_name}.md")
    pages_jsonl_url = azure_storage.save_pages_jsonl(_last_book_id, pages_jsonl_content, f"{base_name}_pages.jsonl")
    sections_jsonl_url = azure_storage.save_sections_jsonl(_last_book_id, sections_jsonl_content, f"{base_name}_sections.jsonl")

    # Update database with URLs and timestamp
    _update_book_urls(
        book_id=_last_book_id,
        html_url=html_url,
        markdown_url=markdown_url,
        pages_jsonl_url=pages_jsonl_url,
        sections_jsonl_url=sections_jsonl_url
    )

    return JSONResponse({
        "ok": True,
        "message": "Generated all files and saved to Azure Blob Storage",
        "book_id": _last_book_id,
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
