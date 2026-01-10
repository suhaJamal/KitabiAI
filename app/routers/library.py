# app/routers/library.py
"""
Library API endpoints for browsing and discovering books.

Endpoints:
- GET /api/books - List all books with filtering and search
- GET /api/books/{book_id} - Get single book details
- GET /api/authors - List all authors
- GET /api/categories - List all categories
- GET /api/stats - Get library statistics
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_

from ..models.database import SessionLocal, Book, Author, Category
from ..models.schemas import BookMetadata

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["library"])


@router.get("/books")
async def list_books(
    language: Optional[str] = Query(None, description="Filter by language: 'ar' or 'en'"),
    author_id: Optional[int] = Query(None, description="Filter by author ID"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    search: Optional[str] = Query(None, description="Search in title, author, description"),
    limit: int = Query(50, ge=1, le=200, description="Number of books to return"),
    offset: int = Query(0, ge=0, description="Number of books to skip"),
    sort: str = Query("newest", description="Sort order: newest, oldest, title_asc, title_desc")
):
    """
    List books with optional filtering and search.

    Query parameters:
        language: Filter by language ('ar' for Arabic, 'en' for English)
        author_id: Filter by author ID
        category_id: Filter by category ID
        search: Search term (searches title, author name, description)
        limit: Maximum number of results (default: 50, max: 200)
        offset: Skip this many results (for pagination)
        sort: Sort order (newest, oldest, title_asc, title_desc)

    Returns:
        JSON with books array and metadata
    """
    db = SessionLocal()
    try:
        # Start with base query
        query = db.query(Book).join(Author)

        # Apply filters
        if language:
            query = query.filter(Book.language == language)

        if author_id:
            query = query.filter(Book.author_id == author_id)

        if category_id:
            query = query.filter(Book.category_id == category_id)

        # Apply search
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Book.title.ilike(search_term),
                    Book.title_ar.ilike(search_term),
                    Author.name.ilike(search_term),
                    Book.description.ilike(search_term),
                    Book.keywords.ilike(search_term)
                )
            )

        # Count total results (before pagination)
        total_count = query.count()

        # Apply sorting
        if sort == "newest":
            query = query.order_by(Book.created_at.desc())
        elif sort == "oldest":
            query = query.order_by(Book.created_at.asc())
        elif sort == "title_asc":
            query = query.order_by(Book.title.asc())
        elif sort == "title_desc":
            query = query.order_by(Book.title.desc())
        else:
            # Default to newest
            query = query.order_by(Book.created_at.desc())

        # Apply pagination
        books = query.limit(limit).offset(offset).all()

        # Format response
        books_list = []
        for book in books:
            books_list.append({
                "id": book.id,
                "title": book.title,
                "title_ar": book.title_ar,
                "author": {
                    "id": book.author.id,
                    "name": book.author.name,
                    "slug": book.author.slug
                },
                "category": {
                    "id": book.category_rel.id,
                    "name": book.category_rel.name,
                    "slug": book.category_rel.slug
                } if book.category_rel else None,
                "language": book.language,
                "description": book.description,
                "keywords": book.keywords,
                "publication_date": book.publication_date,
                "isbn": book.isbn,
                "page_count": book.page_count,
                "section_count": book.section_count,
                "html_url": book.html_url,
                "markdown_url": book.markdown_url,
                "pdf_url": book.pdf_url,
                "cover_image_url": book.cover_image_url,
                "created_at": book.created_at.isoformat() if book.created_at else None,
                "updated_at": book.updated_at.isoformat() if book.updated_at else None,
                "files_generated_at": book.files_generated_at.isoformat() if book.files_generated_at else None,
                "view_count": book.view_count,
                "status": book.status
            })

        return JSONResponse({
            "ok": True,
            "books": books_list,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            },
            "filters": {
                "language": language,
                "author_id": author_id,
                "category_id": category_id,
                "search": search,
                "sort": sort
            }
        })

    except Exception as e:
        logger.error(f"Error listing books: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list books: {str(e)}")
    finally:
        db.close()


@router.get("/books/{book_id}")
async def get_book(book_id: int):
    """
    Get detailed information about a single book.

    Args:
        book_id: Book ID

    Returns:
        Book details with author, category, and file URLs
    """
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()

        if not book:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

        # Increment view count
        book.view_count += 1
        db.commit()

        return JSONResponse({
            "ok": True,
            "book": {
                "id": book.id,
                "title": book.title,
                "title_ar": book.title_ar,
                "author": {
                    "id": book.author.id,
                    "name": book.author.name,
                    "slug": book.author.slug,
                    "bio": book.author.bio
                },
                "category": {
                    "id": book.category_rel.id,
                    "name": book.category_rel.name,
                    "slug": book.category_rel.slug,
                    "description": book.category_rel.description
                } if book.category_rel else None,
                "language": book.language,
                "description": book.description,
                "keywords": book.keywords,
                "publication_date": book.publication_date,
                "isbn": book.isbn,
                "page_count": book.page_count,
                "section_count": book.section_count,
                "html_url": book.html_url,
                "markdown_url": book.markdown_url,
                "pdf_url": book.pdf_url,
                "cover_image_url": book.cover_image_url,
                "pages_jsonl_url": book.pages_jsonl_url,
                "sections_jsonl_url": book.sections_jsonl_url,
                "created_at": book.created_at.isoformat() if book.created_at else None,
                "updated_at": book.updated_at.isoformat() if book.updated_at else None,
                "files_generated_at": book.files_generated_at.isoformat() if book.files_generated_at else None,
                "view_count": book.view_count,
                "status": book.status
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get book: {str(e)}")
    finally:
        db.close()


@router.get("/authors")
async def list_authors(
    language: Optional[str] = Query(None, description="Filter authors by language of their books"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List all authors with book counts.

    Query parameters:
        language: Filter authors by language of their books ('ar' or 'en')
        limit: Maximum number of results
        offset: Skip this many results

    Returns:
        List of authors with book counts
    """
    db = SessionLocal()
    try:
        # Start with base query
        query = db.query(
            Author,
            func.count(Book.id).label('book_count')
        ).join(Book)

        # Filter by language if specified
        if language:
            query = query.filter(Book.language == language)

        # Group by author and order by book count
        query = query.group_by(Author.id).order_by(func.count(Book.id).desc())

        # Apply pagination
        total_count = query.count()
        results = query.limit(limit).offset(offset).all()

        authors_list = []
        for author, book_count in results:
            authors_list.append({
                "id": author.id,
                "name": author.name,
                "name_en": author.name_en,
                "slug": author.slug,
                "bio": author.bio,
                "book_count": book_count,
                "created_at": author.created_at.isoformat() if author.created_at else None
            })

        return JSONResponse({
            "ok": True,
            "authors": authors_list,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
        })

    except Exception as e:
        logger.error(f"Error listing authors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list authors: {str(e)}")
    finally:
        db.close()


@router.get("/categories")
async def list_categories(
    language: Optional[str] = Query(None, description="Filter categories by language of their books"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List all categories with book counts.

    Query parameters:
        language: Filter categories by language of their books ('ar' or 'en')
        limit: Maximum number of results
        offset: Skip this many results

    Returns:
        List of categories with book counts
    """
    db = SessionLocal()
    try:
        # Start with base query
        query = db.query(
            Category,
            func.count(Book.id).label('book_count')
        ).join(Book)

        # Filter by language if specified
        if language:
            query = query.filter(Book.language == language)

        # Group by category and order by book count
        query = query.group_by(Category.id).order_by(func.count(Book.id).desc())

        # Apply pagination
        total_count = query.count()
        results = query.limit(limit).offset(offset).all()

        categories_list = []
        for category, book_count in results:
            categories_list.append({
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "book_count": book_count,
                "created_at": category.created_at.isoformat() if category.created_at else None
            })

        return JSONResponse({
            "ok": True,
            "categories": categories_list,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
        })

    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list categories: {str(e)}")
    finally:
        db.close()


@router.get("/stats")
async def get_stats():
    """
    Get library statistics.

    Returns:
        Statistics about books, authors, categories, pages, and languages
    """
    db = SessionLocal()
    try:
        # Total books
        total_books = db.query(func.count(Book.id)).scalar()

        # Books by language
        arabic_books = db.query(func.count(Book.id)).filter(Book.language == 'ar').scalar()
        english_books = db.query(func.count(Book.id)).filter(Book.language == 'en').scalar()

        # Total authors
        total_authors = db.query(func.count(Author.id)).scalar()

        # Total categories
        total_categories = db.query(func.count(Category.id)).scalar()

        # Total pages
        total_pages = db.query(func.sum(Book.page_count)).scalar() or 0

        # Total sections
        total_sections = db.query(func.sum(Book.section_count)).scalar() or 0

        # Recent books (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_books = db.query(func.count(Book.id)).filter(Book.created_at >= week_ago).scalar()

        return JSONResponse({
            "ok": True,
            "stats": {
                "books": {
                    "total": total_books,
                    "arabic": arabic_books,
                    "english": english_books,
                    "recent_7_days": recent_books
                },
                "authors": {
                    "total": total_authors
                },
                "categories": {
                    "total": total_categories
                },
                "pages": {
                    "total": total_pages
                },
                "sections": {
                    "total": total_sections
                },
                "languages": {
                    "arabic": {
                        "code": "ar",
                        "name": "Arabic",
                        "count": arabic_books
                    },
                    "english": {
                        "code": "en",
                        "name": "English",
                        "count": english_books,
                        "status": "coming_soon" if english_books == 0 else "available"
                    }
                }
            }
        })

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    finally:
        db.close()
