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

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

from ..models.database import SessionLocal, Book, Author, Section, Page, Category
from ..ui.template import html_shell, render_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("", response_class=HTMLResponse)
def admin_page():
    """Render the admin management page with all books."""
    db = SessionLocal()
    try:
        books = (
            db.query(Book)
            .join(Author, Book.author_id == Author.id, isouter=True)
            .order_by(Book.created_at.desc())
            .all()
        )

        books_data = []
        for book in books:
            section_count = db.query(Section).filter(Section.book_id == book.id).count()
            page_count = db.query(Page).filter(Page.book_id == book.id).count()
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
                "created_at": book.created_at.strftime("%Y-%m-%d") if book.created_at else "—",
            })

        return HTMLResponse(html_shell(render_admin(books_data)))
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
