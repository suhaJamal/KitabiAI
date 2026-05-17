# app/services/rag/embedder.py
"""
Chunk-level embeddings for precise RAG retrieval.

Each section's content is split into overlapping chunks whose size depends
on language (Arabic: 200 words, English: 400 words).  Each chunk gets its
own embedding, enabling paragraph-level search instead of section-level
averaging.

Arabic text is normalized before embedding (diacritics stripped, alef/ya
variants unified) so morphological variants match.  The original un-normalized
text is stored in the DB so the LLM still receives natural, readable Arabic.
"""

import logging
import re
from typing import Optional
from openai import OpenAI
from sqlalchemy import text

from ...core.config import settings
from ...models.database import SessionLocal, Book, Section, SectionChunk

logger = logging.getLogger(__name__)

_MODEL         = "text-embedding-3-small"
_MAX_CHARS     = 8000

# English chunk sizes
_CHUNK_WORDS   = 400
_OVERLAP_WORDS = 50

# Arabic chunk sizes — smaller for precision (Arabic words carry more meaning)
_CHUNK_WORDS_AR   = 200
_OVERLAP_WORDS_AR = 25


def normalize_arabic(text: str) -> str:
    """
    Normalize Arabic script before embedding.

    Strips diacritics so حُبّ and حب match.
    Unifies alef forms so أحمد and احمد match.
    Unifies ya forms so على and علي match.

    The original text is preserved for LLM context — only the vector
    passed to OpenAI uses this normalized form.
    """
    if not text:
        return text
    text = re.sub(r'[ً-ٰٟ]', '', text)  # harakat + superscript alef
    text = re.sub(r'ـ', '', text)                   # tatweel (kashida)
    text = re.sub(r'[أإآٱ]', 'ا', text)                 # alef variants → bare alef
    text = re.sub(r'[ىئ]', 'ي', text)                   # alef maqsura / ya-hamza → ya
    text = re.sub(r'ؤ', 'و', text)                       # waw-hamza → waw
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class Embedder:

    def __init__(self):
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured in .env")
        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def embed_book(self, book_id: int) -> dict:
        """
        Split every section into overlapping chunks, embed each chunk,
        and store them in section_chunks. Replaces any previous chunks
        for this book.

        Arabic books use smaller chunks (200 words) and normalized embeddings
        for better precision. English books use 400-word chunks.

        chunk_index conventions:
          -2  book-level metadata (author, category, description) — section_id=NULL
          -1  section title chunk
           0+ content chunks
        """
        db = SessionLocal()
        try:
            # One-time migration: allow metadata chunks with no parent section.
            # DROP NOT NULL is idempotent in PostgreSQL — safe to run every call.
            db.execute(text(
                "ALTER TABLE section_chunks ALTER COLUMN section_id DROP NOT NULL"
            ))
            db.commit()

            book      = db.query(Book).filter(Book.id == book_id).first()
            is_arabic = (book.language if book else 'ar') == 'ar'

            chunk_words   = _CHUNK_WORDS_AR   if is_arabic else _CHUNK_WORDS
            overlap_words = _OVERLAP_WORDS_AR if is_arabic else _OVERLAP_WORDS

            sections = (
                db.query(Section)
                .filter(Section.book_id == book_id)
                .all()
            )

            # Clear old chunks for this book before re-embedding
            db.query(SectionChunk).filter(SectionChunk.book_id == book_id).delete()

            # ── Book metadata chunk (chunk_index = -2) ────────────────────────
            # Embeds author, category, title, description so questions like
            # "من مؤلف الكتاب؟" or "ما تصنيف هذا الكتاب؟" retrieve this directly.
            if book:
                metadata_text  = _build_metadata_text(book, is_arabic)
                meta_to_embed  = normalize_arabic(metadata_text) if is_arabic else metadata_text
                meta_vector    = self.get_embedding(meta_to_embed)
                if meta_vector:
                    db.add(SectionChunk(
                        section_id  = None,        # book-level — no parent section
                        book_id     = book_id,
                        chunk_index = -2,
                        content     = metadata_text,
                        embedding   = meta_vector,
                    ))
                    logger.info(f"Book {book_id}: metadata chunk embedded")

            embedded = 0
            skipped  = 0

            for section in sections:
                content = (section.content or "").strip()
                title   = (section.title   or "").strip()

                # ── Title chunk (chunk_index = -1) ────────────────────────────
                # Embed the section title alone so title-phrased questions
                # retrieve this section even when the content wording differs.
                # Store title + opening 200 words as content so the LLM gets
                # useful context if this chunk is the one retrieved.
                if title:
                    opening_words = content.split()[:200] if content else []
                    title_content = (
                        title + ("\n\n" + " ".join(opening_words) if opening_words else "")
                    )
                    title_to_embed = normalize_arabic(title) if is_arabic else title
                    title_vector   = self.get_embedding(title_to_embed)
                    if title_vector:
                        db.add(SectionChunk(
                            section_id  = section.id,
                            book_id     = book_id,
                            chunk_index = -1,
                            content     = title_content,  # original for LLM readability
                            embedding   = title_vector,
                        ))
                        embedded += 1
                    else:
                        skipped += 1

                # ── Content chunks ────────────────────────────────────────────
                if not content:
                    skipped += 1
                    continue

                chunks = _split_chunks(content, chunk_words, overlap_words)

                for idx, chunk_text in enumerate(chunks):
                    text_to_embed = normalize_arabic(chunk_text) if is_arabic else chunk_text
                    vector        = self.get_embedding(text_to_embed)
                    if not vector:
                        skipped += 1
                        continue

                    db.add(SectionChunk(
                        section_id  = section.id,
                        book_id     = book_id,
                        chunk_index = idx,
                        content     = chunk_text,  # original for LLM readability
                        embedding   = vector,
                    ))
                    embedded += 1

            db.commit()
            logger.info(
                f"Book {book_id} ({'ar' if is_arabic else 'en'}): embedded {embedded} chunks "
                f"across {len(sections)} sections (chunk_words={chunk_words}), skipped {skipped}"
            )
            return {"ok": True, "embedded": embedded, "skipped": skipped}

        except Exception as e:
            db.rollback()
            logger.error(f"Chunk embedding failed for book {book_id}: {e}")
            raise
        finally:
            db.close()

    def get_embedding(self, text: str) -> Optional[list]:
        """Return embedding vector for a single text string."""
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=_MODEL,
                input=text[:_MAX_CHARS],
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding call failed: {e}")
            return None


# ── Metadata helper ───────────────────────────────────────────────────────────

def _build_metadata_text(book: Book, is_arabic: bool) -> str:
    """
    Build a natural-language metadata paragraph from book fields.
    Used for the chunk_index=-2 metadata embedding.
    """
    title = book.title or ""
    for suffix in ('-extract', '-generate', '-auto'):
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
            break

    author   = book.author.name       if book.author       else ""
    category = book.category_rel.name if book.category_rel else ""
    desc     = book.description        or ""
    keywords = book.keywords           or ""
    pub_date = book.publication_date   or ""

    if is_arabic:
        parts = [f"عنوان الكتاب: {title}"]
        if author:   parts.append(f"المؤلف: {author}")
        if category: parts.append(f"التصنيف: {category}")
        if desc:     parts.append(f"وصف الكتاب: {desc}")
        if keywords: parts.append(f"الكلمات المفتاحية: {keywords}")
        if pub_date: parts.append(f"تاريخ النشر: {pub_date}")
    else:
        parts = [f"Book Title: {title}"]
        if author:   parts.append(f"Author: {author}")
        if category: parts.append(f"Category: {category}")
        if desc:     parts.append(f"Description: {desc}")
        if keywords: parts.append(f"Keywords: {keywords}")
        if pub_date: parts.append(f"Publication Date: {pub_date}")

    return "\n".join(parts)


# ── Chunking helpers ──────────────────────────────────────────────────────────

def _split_chunks(content: str, max_words: int, overlap_words: int) -> list:
    """
    Split content into overlapping word-count chunks.
    Respects paragraph boundaries where possible.
    """
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    # Flatten words, inserting a sentinel at paragraph boundaries
    _BREAK = '\x00'
    all_words = []
    for para in paragraphs:
        all_words.extend(para.split())
        all_words.append(_BREAK)

    # Strip trailing sentinel
    while all_words and all_words[-1] == _BREAK:
        all_words.pop()

    if not all_words:
        return [content.strip()] if content.strip() else []

    chunks = []
    start  = 0
    total  = len(all_words)

    while start < total:
        end   = min(start + max_words, total)
        words = all_words[start:end]
        text  = _words_to_text(words, _BREAK)
        if text:
            chunks.append(text)
        if end >= total:
            break
        start = end - overlap_words

    return chunks if chunks else [content[:3000]]


def _words_to_text(words: list, break_sentinel: str) -> str:
    """Re-join word list, converting sentinels back to paragraph breaks."""
    result = []
    buf    = []
    for w in words:
        if w == break_sentinel:
            if buf:
                result.append(' '.join(buf))
                buf = []
        else:
            buf.append(w)
    if buf:
        result.append(' '.join(buf))
    return '\n\n'.join(result).strip()
