# app/services/rag/retriever.py
"""
Chunk-level vector similarity search using pgvector.

Searches section_chunks (paragraph-sized passages) for precise retrieval.
Returns the exact matching passage plus its parent section metadata for citation.
"""

import logging
from sqlalchemy import text

from ...models.database import SessionLocal

logger = logging.getLogger(__name__)


class Retriever:

    def find_relevant_sections(
        self,
        question_embedding: list,
        book_id: int,
        top_k: int = 5,
    ) -> list:
        """
        Return top-K chunks closest to the question embedding.

        Each result dict contains: title, content (the chunk text),
        summary, page_start, page_end, book_title, language, similarity.
        """
        db = SessionLocal()
        try:
            # embedding_str is built from OpenAI floats — inline injection is safe
            embedding_str = "[" + ",".join(str(x) for x in question_embedding) + "]"

            rows = db.execute(
                text(f"""
                    SELECT
                        sc.id,
                        sc.chunk_index,
                        sc.content          AS chunk_content,
                        s.title,
                        s.summary,
                        s.page_start,
                        s.page_end,
                        b.title             AS book_title,
                        b.language,
                        1 - (sc.embedding <=> '{embedding_str}'::vector) AS similarity
                    FROM section_chunks sc
                    JOIN sections s ON s.id = sc.section_id
                    JOIN books    b ON b.id = sc.book_id
                    WHERE sc.book_id = :book_id
                      AND sc.embedding IS NOT NULL
                    ORDER BY sc.embedding <=> '{embedding_str}'::vector
                    LIMIT :top_k
                """),
                {"book_id": book_id, "top_k": top_k},
            ).fetchall()

            results = [
                {
                    "id":         r.id,
                    "title":      r.title,
                    "content":    r.chunk_content,   # exact matching passage
                    "summary":    r.summary,
                    "page_start": r.page_start,
                    "page_end":   r.page_end,
                    "book_title": r.book_title,
                    "language":   r.language,
                    "similarity": round(float(r.similarity), 3),
                }
                for r in rows
            ]

            logger.info(
                f"Retrieved {len(results)} chunks for book {book_id} "
                f"(top similarity: {results[0]['similarity'] if results else 'n/a'})"
            )
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            return []
        finally:
            db.close()
