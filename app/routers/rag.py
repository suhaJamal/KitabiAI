# app/routers/rag.py
"""
RAG endpoints:
- GET  /books/{book_id}       — public book page with chat widget
- POST /api/ask               — answer a question about a specific book
- POST /admin/books/{id}/embed — generate embeddings for all sections
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from ..models.database import SessionLocal, Book, Section, SectionChunk
from ..models.database import Author, Category
from ..services.rag.embedder import Embedder
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

    # Embed question
    question_embedding = _embedder.get_embedding(question)
    if not question_embedding:
        raise HTTPException(status_code=503, detail="Embedding service unavailable")

    # Retrieve relevant sections
    sections = _retriever.find_relevant_sections(question_embedding, book_id, top_k=3)

    if not sections:
        return JSONResponse({
            "answer": "لم يتم إنشاء الفهرس الذكي لهذا الكتاب بعد. يرجى المحاولة لاحقاً." if language == 'ar'
                      else "Smart index not yet generated for this book. Please try later.",
            "sources": []
        })

    # Generate answer
    result = _answerer.answer(question, sections, book_title, language)
    return JSONResponse(result)


# ── Admin: generate embeddings ─────────────────────────────────────────────────

@router.post("/admin/books/{book_id}/embed")
def embed_book(book_id: int):
    """Generate and store embeddings for all sections of a book."""
    try:
        return _embedder.embed_book(book_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Embedding failed for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")
