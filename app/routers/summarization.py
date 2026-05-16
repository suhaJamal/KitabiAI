# app/routers/summarization.py
"""
Admin endpoints for triggering LLM-based book summarization.
"""

import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from ..services.summarization.summarizer import Summarizer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["summarization"])

_summarizer = Summarizer()


def _run_summarization(book_id: int) -> None:
    try:
        result = _summarizer.summarize_book(book_id)
        logger.info(f"Background summarization complete for book {book_id}: {result}")
    except Exception as e:
        logger.error(f"Background summarization failed for book {book_id}: {e}")


@router.post("/books/{book_id}/summarize")
def summarize_book(book_id: int, background_tasks: BackgroundTasks):
    """
    Kick off summarization in the background and return immediately.
    The actual work runs after the response is sent, avoiding gateway timeouts.
    """
    background_tasks.add_task(_run_summarization, book_id)
    return JSONResponse({"ok": True, "status": "started"})
