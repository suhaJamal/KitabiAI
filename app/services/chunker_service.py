# app/services/chunker_service.py
"""
Smart content chunking service.

Strategies:
1. Section-based: Chunk by TOC sections (preserves logical structure)
2. Page-based: Chunk by pages (for image-heavy content)
3. Hybrid: Combine sections with size limits (large sections get split)
"""

import logging
from typing import List, Optional
from ..models.schemas import (
    ChunkInfo, 
    ChunkingReport, 
    SectionInfo, 
    AnalysisReport,
    PageInfo
)

logger = logging.getLogger(__name__)


class ChunkerService:
    """Intelligent content chunking based on structure and content type."""
    
    DEFAULT_MAX_WORDS = 2000  # Maximum words per chunk
    DEFAULT_MIN_WORDS = 100   # Minimum words to avoid tiny chunks
    
    def __init__(self, max_words: int = DEFAULT_MAX_WORDS, min_words: int = DEFAULT_MIN_WORDS):
        self.max_words = max_words
        self.min_words = min_words
    
    def chunk_by_sections(
        self,
        sections: List[SectionInfo],
        pages: List[PageInfo],
        split_large: bool = True
    ) -> ChunkingReport:
        """
        Chunk content by TOC sections (preferred method).
        
        Args:
            sections: List of sections from TOC extraction
            pages: List of pages with content
            split_large: If True, split large sections into smaller chunks
            
        Returns:
            ChunkingReport with section-based chunks
        """
        chunks: List[ChunkInfo] = []
        
        for section in sections:
            # Get pages for this section
            section_pages = self._get_section_pages(section, pages)
            section_content = self._join_page_content(section_pages)
            word_count = self._count_words(section_content)
            
            # Check if section needs splitting
            if split_large and word_count > self.max_words:
                # Split large section into sub-chunks
                sub_chunks = self._split_section(
                    section, 
                    section_pages, 
                    section_content
                )
                chunks.extend(sub_chunks)
            else:
                # Create single chunk for section
                chunk = ChunkInfo(
                    chunk_id=f"{section.section_id}.0",
                    section_id=section.section_id,
                    section_title=section.title,
                    chunk_index=0,
                    page_start=section.page_start,
                    page_end=section.page_end,
                    content=section_content,
                    word_count=word_count,
                    char_count=len(section_content)
                )
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} section-based chunks from {len(sections)} sections")
        
        return ChunkingReport(
            total_chunks=len(chunks),
            chunks=chunks,
            strategy="section-based"
        )
    
    def chunk_by_pages(
        self,
        pages: List[PageInfo],
        pages_per_chunk: int = 5
    ) -> ChunkingReport:
        """
        Chunk content by pages (for image-heavy or non-structured content).
        
        Args:
            pages: List of pages with content
            pages_per_chunk: Number of pages per chunk
            
        Returns:
            ChunkingReport with page-based chunks
        """
        chunks: List[ChunkInfo] = []
        
        for i in range(0, len(pages), pages_per_chunk):
            chunk_pages = pages[i:i + pages_per_chunk]
            content = self._join_page_content(chunk_pages)
            
            page_start = chunk_pages[0].page
            page_end = chunk_pages[-1].page
            chunk_index = i // pages_per_chunk
            
            chunk = ChunkInfo(
                chunk_id=f"page-{chunk_index}",
                section_id="pages",
                section_title=f"Pages {page_start}-{page_end}",
                chunk_index=chunk_index,
                page_start=page_start,
                page_end=page_end,
                content=content,
                word_count=self._count_words(content),
                char_count=len(content)
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} page-based chunks ({pages_per_chunk} pages/chunk)")
        
        return ChunkingReport(
            total_chunks=len(chunks),
            chunks=chunks,
            strategy="page-based"
        )
    
    def smart_chunk(
        self,
        sections: List[SectionInfo],
        pages: List[PageInfo],
        analysis: AnalysisReport
    ) -> ChunkingReport:
        """
        Intelligently choose chunking strategy based on content type.
        
        Args:
            sections: TOC sections
            pages: Page content
            analysis: PDF analysis report
            
        Returns:
            ChunkingReport with optimal chunking strategy
        """
        # For image-only PDFs, use page-based chunking
        if analysis.classification == "image_only":
            logger.info("Using page-based chunking for image-only PDF")
            return self.chunk_by_pages(pages, pages_per_chunk=10)
        
        # For text PDFs with good TOC, use section-based
        if len(sections) > 1:
            logger.info("Using section-based chunking (TOC available)")
            return self.chunk_by_sections(sections, pages, split_large=True)
        
        # Fallback: page-based for unstructured content
        logger.info("Using page-based chunking (fallback)")
        return self.chunk_by_pages(pages, pages_per_chunk=5)
    
    def _get_section_pages(
        self, 
        section: SectionInfo, 
        pages: List[PageInfo]
    ) -> List[PageInfo]:
        """Get pages within a section's range."""
        return [
            p for p in pages 
            if section.page_start <= p.page <= section.page_end
        ]
    
    def _join_page_content(self, pages: List[PageInfo]) -> str:
        """Join text content from multiple pages."""
        texts = [p.text or "" for p in pages if p.has_text]
        return "\n\n".join(texts).strip()
    
    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())
    
    def _split_section(
        self,
        section: SectionInfo,
        pages: List[PageInfo],
        content: str
    ) -> List[ChunkInfo]:
        """
        Split a large section into smaller chunks.
        
        Tries to split at paragraph boundaries while respecting max_words.
        """
        chunks: List[ChunkInfo] = []
        paragraphs = content.split("\n\n")
        
        current_chunk = []
        current_words = 0
        chunk_index = 0
        chunk_start_page = section.page_start
        
        for para in paragraphs:
            para_words = self._count_words(para)
            
            # If adding this paragraph exceeds limit, save current chunk
            if current_chunk and current_words + para_words > self.max_words:
                chunk_content = "\n\n".join(current_chunk)
                
                chunks.append(ChunkInfo(
                    chunk_id=f"{section.section_id}.{chunk_index}",
                    section_id=section.section_id,
                    section_title=section.title,
                    chunk_index=chunk_index,
                    page_start=chunk_start_page,
                    page_end=section.page_end,  # Approximate
                    content=chunk_content,
                    word_count=current_words,
                    char_count=len(chunk_content)
                ))
                
                # Start new chunk
                current_chunk = [para]
                current_words = para_words
                chunk_index += 1
            else:
                current_chunk.append(para)
                current_words += para_words
        
        # Add final chunk
        if current_chunk:
            chunk_content = "\n\n".join(current_chunk)
            chunks.append(ChunkInfo(
                chunk_id=f"{section.section_id}.{chunk_index}",
                section_id=section.section_id,
                section_title=section.title,
                chunk_index=chunk_index,
                page_start=chunk_start_page,
                page_end=section.page_end,
                content=chunk_content,
                word_count=current_words,
                char_count=len(chunk_content)
            ))
        
        logger.info(f"Split section '{section.title}' into {len(chunks)} chunks")
        return chunks