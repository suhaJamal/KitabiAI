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


class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    title_ar = Column(String(500))
    author = Column(String(300))
    author_ar = Column(String(300))
    author_slug = Column(String(200))  # NEW: For clean URLs
    language = Column(String(2), nullable=False)
    category = Column(String(100))
    description = Column(Text)
    keywords = Column(String(500))
    publication_date = Column(String(50))
    isbn = Column(String(20))
    page_count = Column(Integer)
    section_count = Column(Integer)
    html_url = Column(String(500))
    markdown_url = Column(String(500))
    json_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    view_count = Column(Integer, default=0)
    status = Column(String(20), default='published')
    
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


def init_db():
    Base.metadata.create_all(engine)
    print("✅ Tables created/updated successfully!")


if __name__ == "__main__":
    init_db()