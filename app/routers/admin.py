# app/routers/admin.py
"""
Admin router for managing books in the database.

Provides a web-based admin interface to:
- Browse all books with key info
- Edit book metadata (title, author, description, etc.)
- Delete books with all related data (sections, pages)
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import or_

from ..models.database import SessionLocal, Book, Author, Section, Page, Category
from ..services.storage.azure_storage_service import azure_storage
from ..ui.template import html_shell, render_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


_ADMIN_PAGE_SIZE = 20


@router.get("", response_class=HTMLResponse)
def admin_page(search: str = Query(""), page: int = Query(1, ge=1)):
    """Render the admin management page with paginated, searchable book list."""
    db = SessionLocal()
    try:
        # Global stats (unaffected by search/pagination)
        all_books_q = db.query(Book)
        total_all = all_books_q.count()
        total_visible = all_books_q.filter(
            (Book.is_visible == True) | (Book.is_visible == None)
        ).count()
        total_hidden = total_all - total_visible

        # Filtered query
        query = (
            db.query(Book)
            .join(Author, Book.author_id == Author.id, isouter=True)
        )
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(Book.title.ilike(term), Author.name.ilike(term))
            )

        total_filtered = query.count()
        total_pages = max(1, (total_filtered + _ADMIN_PAGE_SIZE - 1) // _ADMIN_PAGE_SIZE)
        page = min(page, total_pages)
        offset = (page - 1) * _ADMIN_PAGE_SIZE

        books = (
            query
            .order_by(Book.created_at.desc())
            .limit(_ADMIN_PAGE_SIZE)
            .offset(offset)
            .all()
        )

        books_data = []
        for book in books:
            section_count = db.query(Section).filter(Section.book_id == book.id).count()
            page_count = db.query(Page).filter(Page.book_id == book.id).count()
            needs_fix = section_count > 0 and db.query(Section).filter(
                Section.book_id == book.id, Section.content.is_(None)
            ).first() is not None
            books_data.append({
                "id": book.id,
                "title": book.title,
                "author": book.author.name if book.author else "Unknown",
                "author_id": book.author_id,
                "language": book.language or "—",
                "page_count": page_count,
                "section_count": section_count,
                "description": book.description or "",
                "category": book.category_rel.name if book.category_rel else "",
                "category_id": book.category_id,
                "keywords": book.keywords or "",
                "publication_date": book.publication_date or "",
                "isbn": book.isbn or "",
                "status": book.status or "published",
                "is_visible": book.is_visible if book.is_visible is not None else True,
                "hidden_reason": book.hidden_reason or "",
                "summary_generated_at": book.summary_generated_at.strftime("%Y-%m-%d") if book.summary_generated_at else None,
                "created_at": book.created_at.strftime("%Y-%m-%d") if book.created_at else "—",
                "needs_fix": needs_fix,
            })

        pagination = {
            "page": page,
            "page_size": _ADMIN_PAGE_SIZE,
            "total": total_filtered,
            "total_pages": total_pages,
            "search": search,
            "total_all": total_all,
            "total_visible": total_visible,
            "total_hidden": total_hidden,
        }

        # All books for the re-extract modal dropdown (unaffected by search/pagination)
        all_books_list = [
            {"id": b.id, "title": b.title}
            for b in db.query(Book).order_by(Book.created_at.desc()).all()
        ]

        return HTMLResponse(html_shell(render_admin(books_data, pagination, all_books_list)))
    finally:
        db.close()


@router.get("/books/{book_id}")
def get_book(book_id: int):
    """Get book data for editing."""
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        return {
            "id": book.id,
            "title": book.title,
            "author": book.author.name if book.author else "",
            "author_id": book.author_id,
            "description": book.description or "",
            "category": book.category_rel.name if book.category_rel else "",
            "category_id": book.category_id,
            "keywords": book.keywords or "",
            "publication_date": book.publication_date or "",
            "isbn": book.isbn or "",
            "cover_image_url": book.cover_image_url or "",
        }
    finally:
        db.close()


@router.put("/books/{book_id}")
async def update_book(book_id: int, data: dict):
    """Update book metadata."""
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Update title
        if "title" in data and data["title"].strip():
            book.title = data["title"].strip()

        # Update author
        if "author" in data and data["author"].strip():
            author_name = data["author"].strip()
            # Find or create author
            author = db.query(Author).filter(Author.name == author_name).first()
            if not author:
                slug = author_name.lower().replace(" ", "-")
                author = Author(name=author_name, slug=slug)
                db.add(author)
                db.flush()
            book.author_id = author.id

        # Update category
        if "category" in data:
            cat_name = data["category"].strip() if data["category"] else ""
            if cat_name:
                category = db.query(Category).filter(Category.name == cat_name).first()
                if not category:
                    slug = cat_name.lower().replace(" ", "-")
                    category = Category(name=cat_name, slug=slug)
                    db.add(category)
                    db.flush()
                book.category_id = category.id
            else:
                book.category_id = None

        # Update simple fields
        if "description" in data:
            book.description = data["description"].strip() if data["description"] else None
        if "keywords" in data:
            book.keywords = data["keywords"].strip() if data["keywords"] else None
        if "publication_date" in data:
            book.publication_date = data["publication_date"].strip() if data["publication_date"] else None
        if "isbn" in data:
            book.isbn = data["isbn"].strip() if data["isbn"] else None

        db.commit()
        logger.info(f"Updated book {book_id}: '{book.title}'")

        return {"ok": True, "message": f"Book '{book.title}' updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/books/{book_id}/cover")
async def upload_cover_image(book_id: int, file: UploadFile = File(...)):
    """Upload or replace a book's cover image."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPG, PNG, WebP, etc.)")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be smaller than 5 MB")

    try:
        url = azure_storage.save_cover_image(book_id, content, file.filename or "cover.jpg")
    except Exception as e:
        logger.error(f"Failed to upload cover for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image to storage")

    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        book.cover_image_url = url
        db.commit()
        logger.info(f"Updated cover image for book {book_id}: {url}")
        return {"ok": True, "cover_image_url": url}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.patch("/books/{book_id}/visibility")
async def update_visibility(book_id: int, data: dict):
    """Toggle book visibility and set optional hidden reason."""
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        book.is_visible = bool(data.get("is_visible", True))
        book.hidden_reason = data.get("hidden_reason", "").strip() or None
        db.commit()

        state = "visible" if book.is_visible else "hidden"
        logger.info(f"Book {book_id} set to {state}")
        return {"ok": True, "is_visible": book.is_visible}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/books/{book_id}")
async def delete_book(book_id: int):
    """Delete a book and all related data (sections, pages)."""
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        book_title = book.title

        # Delete pages first (no cascade set)
        pages_deleted = db.query(Page).filter(Page.book_id == book_id).delete()
        logger.info(f"Deleted {pages_deleted} pages for book {book_id}")

        # Delete book (sections cascade automatically via relationship)
        db.delete(book)
        db.commit()

        logger.info(f"Deleted book {book_id}: '{book_title}'")
        return {"ok": True, "message": f"Book '{book_title}' and all related data deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
