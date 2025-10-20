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
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Artificial Intelligence Ethics",
                "author": "John Smith",
                "publication_date": "2024",
                "isbn": "978-3-16-148410-0"
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