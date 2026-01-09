from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
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

    view_count = Column(Integer, default=0)
    status = Column(String(20), default='published')
    
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
    order_index = Column(Integer)

    book = relationship("Book", back_populates="sections")


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


def init_db():
    Base.metadata.create_all(engine)
    print("✅ Tables created/updated successfully!")


if __name__ == "__main__":
    init_db()