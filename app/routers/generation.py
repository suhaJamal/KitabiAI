# app/routers/generation.py
"""
HTTP routes for content generation (Markdown & HTML).

New endpoints:
- POST /generate/markdown - Generate and download Markdown file
- POST /generate/html - Generate and download HTML file
- GET /generate/chunks - Get chunked data (JSON)
"""

import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from ..services.chunker_service import ChunkerService
from ..services.markdown_generator import MarkdownGenerator
from ..services.html_generator import HtmlGenerator
from ..models.schemas import GenerationRequest, GenerationResponse

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
    _last_book_metadata
)


def _ensure_output_dir():
    """Ensure output directory exists."""
    output_dir = "/mnt/user-data/outputs"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _check_state():
    """Check if we have required state from upload."""
    from .upload import _last_report, _last_book_metadata
    
    if _last_report is None or _last_book_metadata is None:
        raise HTTPException(
            status_code=409,
            detail="No analysis available. Upload a PDF first."
        )


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
        _last_report, _last_filename, _last_pdf_bytes,
        _last_language, _last_book_metadata
    )
    from ..services.toc_extractor import TocExtractor
    
    # Extract TOC
    toc_extractor = TocExtractor()
    sections_report = toc_extractor.extract(_last_pdf_bytes)
    
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
        _last_report, _last_filename, _last_pdf_bytes,
        _last_language, _last_book_metadata
    )
    from ..services.toc_extractor import TocExtractor
    from fastapi.responses import HTMLResponse
    
    # Extract TOC
    toc_extractor = TocExtractor()
    sections_report = toc_extractor.extract(_last_pdf_bytes)
    
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
    
    from .upload import _last_report, _last_pdf_bytes
    from ..services.toc_extractor import TocExtractor
    
    # Extract TOC
    toc_extractor = TocExtractor()
    sections_report = toc_extractor.extract(_last_pdf_bytes)
    
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
    Generate both Markdown and HTML files.
    
    Returns URLs for both generated files.
    """
    _check_state()
    
    from .upload import (
        _last_report, _last_filename, _last_pdf_bytes,
        _last_language, _last_book_metadata
    )
    from ..services.toc_extractor import TocExtractor
    
    # Extract TOC (once)
    toc_extractor = TocExtractor()
    sections_report = toc_extractor.extract(_last_pdf_bytes)
    
    output_dir = _ensure_output_dir()
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
    
    md_filename = f"{base_name}.md"
    md_path = os.path.join(output_dir, md_filename)
    md_generator.save_to_file(markdown_content, md_path)
    
    # Generate HTML
    html_content = html_generator.generate(
        metadata=_last_book_metadata,
        sections=sections_report.sections,
        pages=_last_report.pages,
        language=_last_language,
        include_toc=include_toc
    )
    
    html_filename = f"{base_name}.html"
    html_path = os.path.join(output_dir, html_filename)
    html_generator.save_to_file(html_content, html_path)
    
    return JSONResponse({
        "ok": True,
        "message": "Generated both Markdown and HTML",
        "files": [
            {
                "format": "markdown",
                "filename": md_filename,
                "size_bytes": len(markdown_content.encode('utf-8')),
                "download_url": f"computer:///mnt/user-data/outputs/{md_filename}"
            },
            {
                "format": "html",
                "filename": html_filename,
                "size_bytes": len(html_content.encode('utf-8')),
                "download_url": f"computer:///mnt/user-data/outputs/{html_filename}"
            }
        ],
        "sections_count": len(sections_report.sections)
    })