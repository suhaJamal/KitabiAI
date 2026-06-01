from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Author(Base):
    """Author table - stores unique authors"""
    __tablename__ = "authors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(300), nullable=False, unique=True)  # Unique constraint
    name_en = Column(String(300))  # Optional English name
    slug = Column(String(200), nullable=False, unique=True)  # URL-friendly
    bio = Column(Text)  # Optional biography
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship: one author has many books
    books = relationship("Book", back_populates="author")

class Category(Base):
    """Category table - stores book categories"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)  # Unique constraint
    slug = Column(String(100), nullable=False, unique=True)  # URL-friendly
    description = Column(Text)  # Optional description
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship: one category has many books
    books = relationship("Book", back_populates="category_rel")

class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    title_ar = Column(String(500))
    
    # CHANGED: Foreign keys instead of direct author/category strings
    author_id = Column(Integer, ForeignKey('authors.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))  # Optional
    
    language = Column(String(2), nullable=False)
    description = Column(Text)
    keywords = Column(String(500))
    publication_date = Column(String(50))
    isbn = Column(String(20))
    page_count = Column(Integer)
    section_count = Column(Integer)

    # Generated file URLs (populated after generation)
    html_url = Column(String(500))
    markdown_url = Column(String(500))
    pages_jsonl_url = Column(String(500))      # Page-level analysis JSONL
    sections_jsonl_url = Column(String(500))   # TOC sections JSONL

    # Source file URLs (populated during/after upload)
    pdf_url = Column(String(500))              # Original PDF in Azure Blob Storage
    cover_image_url = Column(String(500))      # Book cover image

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    files_generated_at = Column(DateTime)      # When HTML/Markdown/JSON files were generated

    summary = Column(Text)
    summary_generated_at = Column(DateTime)

    view_count = Column(Integer, default=0)
    status = Column(String(20), default='published')
    is_visible = Column(Boolean, default=True)
    hidden_reason = Column(Text, nullable=True)
    
    # Relationships
    author = relationship("Author", back_populates="books")
    category_rel = relationship("Category", back_populates="books")
    sections = relationship("Section", back_populates="book", cascade="all, delete-orphan")


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    title = Column(String(500))
    level = Column(Integer)
    page_start = Column(Integer)
    page_end = Column(Integer)
    content = Column(Text)
    summary = Column(Text)
    embedding = Column(Vector(1536))
    order_index = Column(Integer)

    book = relationship("Book", back_populates="sections")


class SectionChunk(Base):
    """Chunk-level embeddings for precise RAG retrieval."""
    __tablename__ = "section_chunks"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    section_id  = Column(Integer, ForeignKey('sections.id', ondelete='CASCADE'), nullable=True)  # nullable for book-level metadata chunks (chunk_index=-2)
    book_id     = Column(Integer, ForeignKey('books.id',    ondelete='CASCADE'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content     = Column(Text, nullable=False)
    embedding   = Column(Vector(1536))


class Page(Base):
    """Page table - stores extracted text content for each page"""
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    page_number = Column(Integer, nullable=False)  # 1-indexed page number
    text = Column(Text)  # Extracted text content
    word_count = Column(Integer)  # Number of words on this page
    char_count = Column(Integer)  # Number of characters
    has_images = Column(Integer, default=0)  # Number of images on page
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    book = relationship("Book", backref="pages")


class WaitlistEntry(Base):
    """Email waitlist — people who want to stay updated about KitabiAI."""
    __tablename__ = "waitlist"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(200))
    email      = Column(String(300), nullable=False, unique=True)
    source     = Column(String(50))   # 'library' or 'marketing'
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatRateLimit(Base):
    """Tracks how many chatbot questions each IP has asked per book. No reset."""
    __tablename__ = "chat_rate_limits"

    id      = Column(Integer, primary_key=True, autoincrement=True)
    ip      = Column(String(45), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    count   = Column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint('ip', 'book_id', name='uq_chat_rate_ip_book'),)


class BookFeedback(Base):
    """User-submitted feedback from a book page."""
    __tablename__ = "book_feedback"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    book_id       = Column(Integer, ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    book_title    = Column(String(500))
    feedback_type = Column(String(30), nullable=False)  # toc / missing_pages / quality / other
    message       = Column(Text, nullable=False)
    name          = Column(String(200))
    email         = Column(String(300))
    page_number   = Column(Integer)
    status        = Column(String(20), default='new')   # new / reviewed / resolved
    ip            = Column(String(45))
    created_at    = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)
    print("✅ Tables created/updated successfully!")


if __name__ == "__main__":
    init_db()