# app/routers/feedback.py
"""
Feedback router.

Public:
  POST /api/feedback  — submit feedback from a book page

Admin:
  GET  /admin/feedback       — view all feedback
  PATCH /admin/feedback/{id} — update status (new/reviewed/resolved)
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ..models.database import SessionLocal, BookFeedback, Book
from ..ui.template import html_shell, render_admin_feedback

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])

_ALLOWED_TYPES = {"toc", "missing_pages", "quality", "other"}


@router.post("/api/feedback")
async def submit_feedback(request: Request, data: dict):
    """Accept feedback submitted from a book page."""
    book_id = data.get("book_id")
    feedback_type = data.get("feedback_type", "other")
    message = (data.get("message") or "").strip()

    if not book_id or not message:
        raise HTTPException(status_code=400, detail="book_id and message are required")
    if feedback_type not in _ALLOWED_TYPES:
        feedback_type = "other"

    ip = request.client.host if request.client else None

    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        entry = BookFeedback(
            book_id=book_id,
            book_title=book.title,
            feedback_type=feedback_type,
            message=message,
            name=(data.get("name") or "").strip() or None,
            email=(data.get("email") or "").strip() or None,
            page_number=data.get("page_number") or None,
            ip=ip,
        )
        db.add(entry)
        db.commit()
        logger.info(f"Feedback submitted for book {book_id}: {feedback_type}")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    finally:
        db.close()


@router.get("/admin/feedback", response_class=HTMLResponse)
def admin_feedback_page():
    """Render the admin feedback list."""
    db = SessionLocal()
    try:
        entries = (
            db.query(BookFeedback)
            .order_by(BookFeedback.created_at.desc())
            .limit(300)
            .all()
        )
        data = [
            {
                "id": e.id,
                "book_id": e.book_id,
                "book_title": e.book_title or "",
                "feedback_type": e.feedback_type,
                "message": e.message,
                "name": e.name or "",
                "email": e.email or "",
                "page_number": e.page_number,
                "status": e.status or "new",
                "ip": e.ip or "",
                "created_at": e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else "",
            }
            for e in entries
        ]
        return HTMLResponse(html_shell(render_admin_feedback(data)))
    finally:
        db.close()


@router.patch("/admin/feedback/{feedback_id}")
async def update_feedback_status(feedback_id: int, data: dict):
    """Update the status of a feedback entry."""
    new_status = data.get("status", "reviewed")
    if new_status not in ("new", "reviewed", "resolved"):
        raise HTTPException(status_code=400, detail="Invalid status")

    db = SessionLocal()
    try:
        entry = db.query(BookFeedback).filter(BookFeedback.id == feedback_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Feedback not found")
        entry.status = new_status
        db.commit()
        return {"ok": True, "status": entry.status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
