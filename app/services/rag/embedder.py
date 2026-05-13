# app/services/rag/embedder.py
"""
Chunk-level embeddings for precise RAG retrieval.

Each section's content is split into ~400-word overlapping chunks.
Each chunk gets its own embedding, enabling paragraph-level search
instead of section-level averaging.
"""

import logging
from typing import Optional
from openai import OpenAI

from ...core.config import settings
from ...models.database import SessionLocal, Section, SectionChunk

logger = logging.getLogger(__name__)

_MODEL         = "text-embedding-3-small"
_MAX_CHARS     = 8000
_CHUNK_WORDS   = 400
_OVERLAP_WORDS = 50


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
        """
        db = SessionLocal()
        try:
            sections = (
                db.query(Section)
                .filter(Section.book_id == book_id)
                .all()
            )

            # Clear old chunks for this book before re-embedding
            db.query(SectionChunk).filter(SectionChunk.book_id == book_id).delete()

            embedded = 0
            skipped  = 0

            for section in sections:
                content = (section.content or "").strip()
                if not content:
                    skipped += 1
                    continue

                chunks = _split_chunks(content, _CHUNK_WORDS, _OVERLAP_WORDS)

                for idx, chunk_text in enumerate(chunks):
                    vector = self.get_embedding(chunk_text)
                    if not vector:
                        skipped += 1
                        continue

                    db.add(SectionChunk(
                        section_id  = section.id,
                        book_id     = book_id,
                        chunk_index = idx,
                        content     = chunk_text,
                        embedding   = vector,
                    ))
                    embedded += 1

            db.commit()
            logger.info(
                f"Book {book_id}: embedded {embedded} chunks across "
                f"{len(sections)} sections, skipped {skipped}"
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
