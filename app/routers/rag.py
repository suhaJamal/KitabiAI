# app/routers/rag.py
"""
RAG endpoints:
- GET  /books/{book_id}       — public book page with chat widget
- POST /api/ask               — answer a question about a specific book
- POST /admin/books/{id}/embed — generate embeddings for all sections
"""

import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from ..models.database import SessionLocal, Book, Section, SectionChunk, Page
from ..models.database import Author, Category
from ..services.rag.embedder import Embedder, normalize_arabic
from ..services.rag.retriever import Retriever
from ..services.rag.answerer import Answerer
from ..ui.book_template import render_book_page

logger = logging.getLogger(__name__)
router = APIRouter()

_embedder = Embedder()
_retriever = Retriever()
_answerer = Answerer()


# ── Public book page ──────────────────────────────────────────────────────────

@router.get("/books/{book_id}", response_class=HTMLResponse)
def book_page(book_id: int):
    """Render the public book page with content and chat widget."""
    db = SessionLocal()
    try:
        book = (
            db.query(Book)
            .join(Author, isouter=True)
            .filter(Book.id == book_id)
            .first()
        )
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        sections = (
            db.query(Section)
            .filter(Section.book_id == book_id)
            .order_by(Section.order_index)
            .all()
        )

        has_embeddings = (
            db.query(SectionChunk)
            .filter(SectionChunk.book_id == book_id,
                    SectionChunk.embedding.isnot(None))
            .first() is not None
        )

        return HTMLResponse(render_book_page(book, sections, has_embeddings))
    finally:
        db.close()


# ── Ask endpoint (RAG) ────────────────────────────────────────────────────────

@router.post("/api/ask")
def ask(data: dict):
    """
    Answer a question about a specific book using RAG.

    Body: { "book_id": int, "question": str }
    Returns: { "answer": str, "sources": [...] }
    """
    book_id = data.get("book_id")
    question = (data.get("question") or "").strip()

    if not book_id:
        raise HTTPException(status_code=400, detail="book_id is required")
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        book_title = book.title
        language = book.language or 'ar'
    finally:
        db.close()

    # Strip TOC method suffix from title for display
    for suffix in ('-extract', '-generate', '-auto'):
        if book_title.endswith(suffix):
            book_title = book_title[:-len(suffix)].strip()
            break

    # Embed question — normalize Arabic queries to match normalized embeddings
    question_to_embed = normalize_arabic(question) if language == 'ar' else question
    question_embedding = _embedder.get_embedding(question_to_embed)
    if not question_embedding:
        raise HTTPException(status_code=503, detail="Embedding service unavailable")

    # Retrieve relevant sections
    sections = _retriever.find_relevant_sections(question_embedding, book_id, top_k=8)

    if not sections:
        return JSONResponse({
            "answer": "لم يتم إنشاء الفهرس الذكي لهذا الكتاب بعد. يرجى المحاولة لاحقاً." if language == 'ar'
                      else "Smart index not yet generated for this book. Please try later.",
            "sources": []
        })

    # Generate answer
    result = _answerer.answer(question, sections, book_title, language)
    return JSONResponse(result)


# ── Admin: fix missing section content from pages table ───────────────────────

@router.post("/admin/books/{book_id}/fix-content")
def fix_book_content(book_id: int):
    """
    Populate Section.content from the pages table for any section that has
    NULL content. Uses the section's page_start/page_end range to concatenate
    stored page text — no PDF re-upload or Azure DI call required.
    """
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        sections = (
            db.query(Section)
            .filter(Section.book_id == book_id, Section.content.is_(None))
            .order_by(Section.order_index)
            .all()
        )

        fixed = 0
        skipped = 0
        for section in sections:
            if section.page_start is None:
                skipped += 1
                continue
            page_end = section.page_end or section.page_start
            pages = (
                db.query(Page)
                .filter(
                    Page.book_id == book_id,
                    Page.page_number >= section.page_start,
                    Page.page_number <= page_end,
                )
                .order_by(Page.page_number)
                .all()
            )
            text = '\n\n'.join(p.text for p in pages if p.text and p.text.strip())
            if text:
                section.content = text
                fixed += 1
            else:
                skipped += 1

        db.commit()
        return JSONResponse({"ok": True, "fixed": fixed, "skipped": skipped})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"fix-content failed for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ── Admin: generate embeddings ─────────────────────────────────────────────────

def _run_embedding(book_id: int) -> None:
    try:
        result = _embedder.embed_book(book_id)
        logger.info(f"Background embedding complete for book {book_id}: {result}")
    except Exception as e:
        logger.error(f"Background embedding failed for book {book_id}: {e}")


@router.post("/admin/books/{book_id}/embed")
def embed_book(book_id: int, background_tasks: BackgroundTasks):
    """Kick off embedding in the background and return immediately."""
    background_tasks.add_task(_run_embedding, book_id)
    return JSONResponse({"ok": True, "status": "started"})
