# app/routers/rag.py
"""
RAG endpoints:
- GET  /books/{book_id}       — public book page with chat widget
- POST /api/ask               — answer a question about a specific book
- POST /admin/books/{id}/embed — generate embeddings for all sections
"""

import logging
import re
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ..models.database import SessionLocal, Book, Section, SectionChunk, Page
from ..models.database import Author, Category, ChatRateLimit
from ..services.rag.embedder import Embedder, normalize_arabic
from ..services.rag.retriever import Retriever
from ..services.rag.answerer import Answerer
from ..ui.book_template import render_book_page
from ..core.config import settings


def _detect_lang(text: str) -> str:
    """Return 'ar' if text contains Arabic characters, else 'en'."""
    return 'ar' if re.search(r'[؀-ۿ]', text) else 'en'


# Ordered longest-first to avoid partial matches (e.g. "الثاني" inside "الثاني عشر")
_AR_ORDINALS = [
    (12, 'الثاني عشر'), (11, 'الحادي عشر'), (10, 'العاشر'),
    (9, 'التاسع'), (8, 'الثامن'), (7, 'السابع'), (6, 'السادس'),
    (5, 'الخامس'), (4, 'الرابع'), (3, 'الثالث'), (2, 'الثاني'), (1, 'الأول'),
]
_EN_CHAPTER_WORDS = [
    (12, 'twelve'), (11, 'eleven'), (10, 'ten'),
    (9, 'nine'), (8, 'eight'), (7, 'seven'), (6, 'six'),
    (5, 'five'), (4, 'four'), (3, 'three'), (2, 'two'), (1, 'one'),
    (12, 'twelfth'), (11, 'eleventh'), (10, 'tenth'),
    (9, 'ninth'), (8, 'eighth'), (7, 'seventh'), (6, 'sixth'),
    (5, 'fifth'), (4, 'fourth'), (3, 'third'), (2, 'second'), (1, 'first'),
]


def _detect_chapter_number(question: str) -> int | None:
    """Return chapter number if question explicitly mentions one, else None."""
    # Arabic: "الفصل السادس"
    for num, word in _AR_ORDINALS:
        if re.search(rf'الفصل\s+{re.escape(word)}', question):
            return num

    # English: "chapter six" / "chapter sixth" / "chapter 6"
    q_lower = question.lower()
    for num, word in _EN_CHAPTER_WORDS:
        if re.search(rf'\bchapter\s+{word}\b', q_lower):
            return num
    m = re.search(r'\bchapter\s+(\d{1,2})\b', q_lower)
    if m:
        return int(m.group(1))

    # Digit after الفصل: "الفصل 6"
    m = re.search(r'الفصل\s+(\d{1,2})', question)
    if m:
        return int(m.group(1))

    return None


def _boost_chapter(sections: list, chapter_num: int) -> list:
    """Move chunks belonging to the detected chapter to the front of results."""
    ar_word = next((w for n, w in _AR_ORDINALS if n == chapter_num), '')
    target, rest = [], []
    for s in sections:
        title = s.get('title', '')
        is_match = (
            (ar_word and ar_word in title) or
            re.search(rf'\bchapter\s*{chapter_num}\b', title, re.IGNORECASE) is not None
        )
        if is_match:
            s = dict(s)
            s['similarity'] = 2.0  # override so answerer's sort keeps this first
            target.append(s)
        else:
            rest.append(s)
    return target + rest


_AR_STOP = frozenset({
    'في', 'من', 'على', 'إلى', 'هذا', 'هذه', 'التي', 'الذي', 'مع', 'عن',
    'أن', 'لا', 'ما', 'هو', 'هي', 'إن', 'كان', 'كل', 'قد', 'لم', 'لن',
    'بين', 'حتى', 'عند', 'بعد', 'قبل', 'حول', 'خلال', 'ذلك', 'هل',
    'وفي', 'وهو', 'وهي', 'فى', 'بعض', 'حيث', 'هنا', 'هناك', 'عليه',
})
_EN_STOP = frozenset({
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'was',
    'will', 'what', 'from', 'this', 'that', 'with', 'have', 'been', 'more',
    'when', 'who', 'how', 'tell', 'summarize', 'summarise', 'explain',
    'describe', 'about', 'please', 'give', 'write', 'list',
})


def _kw_set(text: str) -> set:
    """Extract significant keywords from text for title matching."""
    ar = {normalize_arabic(w) for w in re.findall(r'[؀-ۿ]{3,}', text)
          if w not in _AR_STOP and normalize_arabic(w) not in _AR_STOP}
    en = {w.lower() for w in re.findall(r'[a-zA-Z]{4,}', text)
          if w.lower() not in _EN_STOP}
    return ar | en


def _boost_title_keywords(sections: list, question: str) -> list:
    """Boost sections whose title shares ≥2 significant keywords with the question."""
    q_kw = _kw_set(question)
    if len(q_kw) < 2:
        return sections
    target, rest = [], []
    for s in sections:
        overlap = q_kw & _kw_set(s.get('title', ''))
        if len(overlap) >= 2:
            s = dict(s)
            s['similarity'] = 2.0
            target.append(s)
        else:
            rest.append(s)
    return target + rest


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
def ask(data: dict, request: Request):
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

    # Bypass check — cookie set by admin skips rate limiting
    bypass_key = request.cookies.get("rl_bypass", "")
    is_bypass = bool(
        settings.RATE_LIMIT_BYPASS_KEY and
        bypass_key == settings.RATE_LIMIT_BYPASS_KEY
    )

    # Client IP — respect X-Forwarded-For from reverse proxy
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
    )

    # Rate limit check
    if not is_bypass:
        db = SessionLocal()
        try:
            rl = db.query(ChatRateLimit).filter_by(ip=client_ip, book_id=book_id).first()
            if rl and rl.count >= settings.CHAT_QUESTIONS_LIMIT:
                lang_hint = _detect_lang(question)
                msg = (
                    "لقد استنفدت عدد الأسئلة المسموح بها لهذا الكتاب. شكراً لاهتمامك بـ KitabiAI!"
                    if lang_hint == 'ar'
                    else "You've reached the question limit for this book. Thank you for trying KitabiAI!"
                )
                return JSONResponse({"answer": msg, "sources": [], "limit_reached": True})
        finally:
            db.close()

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

    # Detect language of the question (independent of book language)
    question_lang = _detect_lang(question)

    # Embed question — normalize only Arabic queries to match normalized book embeddings
    question_to_embed = normalize_arabic(question) if question_lang == 'ar' else question
    question_embedding = _embedder.get_embedding(question_to_embed)
    if not question_embedding:
        raise HTTPException(status_code=503, detail="Embedding service unavailable")

    # Retrieve relevant sections
    sections = _retriever.find_relevant_sections(question_embedding, book_id, top_k=8)

    # Boost detected chapter to front so sources reflect the correct chapter
    chapter_num = _detect_chapter_number(question)
    if chapter_num:
        sections = _boost_chapter(sections, chapter_num)

    # Boost sections whose title shares keywords with the question (handles title references)
    sections = _boost_title_keywords(sections, question)

    if not sections:
        no_index_msg = (
            "لم يتم إنشاء الفهرس الذكي لهذا الكتاب بعد. يرجى المحاولة لاحقاً."
            if question_lang == 'ar'
            else "Smart index not yet generated for this book. Please try later."
        )
        return JSONResponse({"answer": no_index_msg, "sources": []})

    # Generate answer — respond in the language the question was asked in
    result = _answerer.answer(question, sections, book_title, language,
                              question_language=question_lang)

    # Increment counter after a successful answer
    if not is_bypass:
        db = SessionLocal()
        try:
            rl = db.query(ChatRateLimit).filter_by(ip=client_ip, book_id=book_id).first()
            if rl:
                rl.count += 1
            else:
                rl = ChatRateLimit(ip=client_ip, book_id=book_id, count=1)
                db.add(rl)
            db.commit()
            result["questions_remaining"] = max(0, settings.CHAT_QUESTIONS_LIMIT - rl.count)
        finally:
            db.close()

    return JSONResponse(result)


# ── Admin: re-run Azure DI extraction with table support ──────────────────────

@router.post("/admin/books/{book_id}/reextract")
def reextract_book(book_id: int):
    """
    Download the stored PDF, re-run Azure DI extraction (with Markdown table
    support), update the pages table, then rebuild all section content.
    """
    from ..services.storage.azure_storage_service import azure_storage
    from ..services.detection.language_detector import LanguageDetector

    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if not book.pdf_url:
            raise HTTPException(status_code=400, detail="No PDF stored for this book. Re-upload the book first.")

        # 1. Download PDF from blob storage
        logger.info(f"Re-extract book {book_id}: downloading PDF from {book.pdf_url}")
        pdf_bytes = azure_storage.download_pdf(book.pdf_url)

        # 2. Re-run Azure DI (table-aware extraction)
        detector = LanguageDetector()
        extracted_text, _ = detector._extract_with_azure(pdf_bytes)

        # 3. Split by page boundaries and update pages table
        page_texts = extracted_text.split('\f')
        pages = (
            db.query(Page)
            .filter(Page.book_id == book_id)
            .order_by(Page.page_number)
            .all()
        )
        pages_updated = 0
        for pg in pages:
            idx = pg.page_number - 1
            if idx < len(page_texts):
                new_text = page_texts[idx].strip()
                if new_text != (pg.text or '').strip():
                    pg.text = new_text
                    pages_updated += 1

        # 4. Rebuild ALL section content from updated pages
        sections = (
            db.query(Section)
            .filter(Section.book_id == book_id)
            .order_by(Section.order_index)
            .all()
        )
        sections_fixed = 0
        for section in sections:
            if section.page_start is None:
                continue
            page_end = section.page_end or section.page_start
            section_pages = [
                p for p in pages
                if section.page_start <= p.page_number <= page_end
            ]
            text = '\n\n'.join(
                p.text for p in section_pages if p.text and p.text.strip()
            )
            if text:
                section.content = text
                sections_fixed += 1

        db.commit()
        logger.info(f"Re-extract book {book_id}: {pages_updated} pages updated, {sections_fixed} sections rebuilt")
        return JSONResponse({
            "ok": True,
            "pages_updated": pages_updated,
            "sections_fixed": sections_fixed,
        })

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"reextract failed for book {book_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


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
