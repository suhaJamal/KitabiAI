# app/routers/summarization.py
"""
Admin endpoints for triggering LLM-based book summarization.
"""

import logging
from fastapi import APIRouter, HTTPException
from ..services.summarization.summarizer import Summarizer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["summarization"])

_summarizer = Summarizer()


@router.post("/books/{book_id}/summarize")
def summarize_book(book_id: int):
    """
    Trigger summarization for all sections of a book, then generate a
    book-level summary. Synchronous — admin waits for completion.

    Returns counts of summarized/skipped sections.
    """
    try:
        return _summarizer.summarize_book(book_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Summarization failed for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")
