"""
Pydantic data models (request/response/domain).

- PageInfo, AnalysisReport, and future models for exports/TOC.
- Ensures validated, typed data passed between services and routers.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional

class PageInfo(BaseModel):
    page: int
    has_text: bool
    image_count: int
    text: Optional[str] = None

class AnalysisReport(BaseModel):
    num_pages: int
    pages: List[PageInfo]
    classification: Literal["image_only", "text_only", "mixed"]

# TOC/Sections models
class SectionInfo(BaseModel):
    section_id: str
    title: str
    level: int
    page_start: int  # inclusive, 1-based
    page_end: int    # inclusive, 1-based

class SectionsReport(BaseModel):  # note the "s" (plural)
    bookmarks_found: bool
    sections: List[SectionInfo]

# Book metadata models
class BookMetadata(BaseModel):
    """User-provided book metadata."""
    title: str = Field(..., description="Book title (required)")
    author: Optional[str] = Field(None, description="Author name")
    publication_date: Optional[str] = Field(None, description="Publication date")
    isbn: Optional[str] = Field(None, description="ISBN number")

    # SEO fields (optional)
    description: Optional[str] = Field(None, max_length=160, description="Brief book description for SEO (max 160 characters)")
    category: Optional[str] = Field(None, description="Book category/subject (e.g., Philosophy, History)")
    keywords: Optional[str] = Field(None, description="Comma-separated keywords/tags")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Artificial Intelligence Ethics",
                "author": "John Smith",
                "publication_date": "2024",
                "isbn": "978-3-16-148410-0",
                "description": "A comprehensive exploration of ethical considerations in artificial intelligence and machine learning applications.",
                "category": "Technology",
                "keywords": "AI, ethics, machine learning, technology, philosophy"
            }
        }
    )

class BookInfo(BaseModel):
    """Complete book information including metadata and analysis results."""
    # User-provided metadata
    metadata: BookMetadata
    
    # Auto-detected information
    language: str = Field(..., description="Detected language (english/arabic)")
    classification: str = Field(..., description="PDF classification")
    num_pages: int = Field(..., description="Total page count")
    filename: str = Field(..., description="Original filename")
    
    # Timestamps
    uploaded_at: Optional[str] = Field(None, description="Upload timestamp (ISO format)")

# Chunking models
class ChunkInfo(BaseModel):
    """Information about a content chunk."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    section_id: str = Field(..., description="Parent section ID")
    section_title: str = Field(..., description="Section title")
    chunk_index: int = Field(..., description="Index within section (0-based)")
    page_start: int = Field(..., description="Starting page number")
    page_end: int = Field(..., description="Ending page number")
    content: str = Field(..., description="Chunk text content")
    word_count: int = Field(..., description="Number of words in chunk")
    char_count: int = Field(..., description="Number of characters")

class ChunkingReport(BaseModel):
    """Report of chunking results."""
    total_chunks: int
    chunks: List[ChunkInfo]
    strategy: str = Field(..., description="Chunking strategy used")
    
# Generation models
class GenerationFormat(str):
    """Available generation formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    BOTH = "both"

class GenerationRequest(BaseModel):
    """Request for content generation."""
    format: str = Field(..., description="Output format: markdown, html, or both")
    include_toc: bool = Field(True, description="Include table of contents")
    include_metadata: bool = Field(True, description="Include book metadata")
    chunk_size: Optional[int] = Field(None, description="Words per chunk (None = section-based)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "format": "markdown",
                "include_toc": True,
                "include_metadata": True,
                "chunk_size": None
            }
        }
    )

class GenerationResponse(BaseModel):
    """Response from content generation."""
    format: str
    filename: str
    size_bytes: int
    sections_count: int
    chunks_count: Optional[int] = None
    download_url: str