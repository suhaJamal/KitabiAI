# app/services/markdown_generator.py
"""
Generate clean, structured Markdown from PDF content.

Features:
- Hierarchical structure from TOC
- Metadata frontmatter
- Clean formatting for both Arabic and English
- Section-based organization
"""

import logging
from typing import List, Optional
from datetime import datetime
from ..models.schemas import (
    BookMetadata,
    SectionInfo,
    PageInfo,
    ChunkInfo
)

logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Generate structured Markdown from book content."""
    
    def generate(
        self,
        metadata: BookMetadata,
        sections: List[SectionInfo],
        pages: List[PageInfo],
        language: str,
        include_toc: bool = True,
        include_metadata: bool = True
    ) -> str:
        """
        Generate complete Markdown document.
        
        Args:
            metadata: Book metadata
            sections: TOC sections
            pages: Page content
            language: Detected language (english/arabic)
            include_toc: Include table of contents
            include_metadata: Include frontmatter
            
        Returns:
            Complete Markdown document as string
        """
        parts = []
        
        # 1. Frontmatter (YAML-style metadata)
        if include_metadata:
            parts.append(self._generate_frontmatter(metadata, language))
        
        # 2. Title page
        parts.append(self._generate_title_page(metadata))
        
        # 3. Table of contents
        if include_toc and len(sections) > 1:
            parts.append(self._generate_toc(sections))
        
        # 4. Content sections
        for section in sections:
            section_md = self._generate_section(section, pages, language)
            parts.append(section_md)
        
        # Join all parts with proper spacing
        return "\n\n---\n\n".join(parts)
    
    def generate_from_chunks(
        self,
        metadata: BookMetadata,
        chunks: List[ChunkInfo],
        language: str,
        include_toc: bool = True,
        include_metadata: bool = True
    ) -> str:
        """
        Generate Markdown from pre-chunked content.
        
        Args:
            metadata: Book metadata
            chunks: Chunked content
            language: Detected language
            include_toc: Include table of contents
            include_metadata: Include frontmatter
            
        Returns:
            Complete Markdown document
        """
        parts = []
        
        # 1. Frontmatter
        if include_metadata:
            parts.append(self._generate_frontmatter(metadata, language))
        
        # 2. Title page
        parts.append(self._generate_title_page(metadata))
        
        # 3. Table of contents (from chunks)
        if include_toc:
            parts.append(self._generate_toc_from_chunks(chunks))
        
        # 4. Content from chunks
        current_section = None
        for chunk in chunks:
            # Add section header if new section
            if chunk.section_id != current_section:
                parts.append(f"## {chunk.section_title}\n")
                current_section = chunk.section_id
            
            # Add chunk content
            parts.append(chunk.content)
        
        return "\n\n---\n\n".join(parts)
    
    def _generate_frontmatter(self, metadata: BookMetadata, language: str) -> str:
        """Generate YAML frontmatter with metadata."""
        lines = ["---"]
        lines.append(f"title: {metadata.title}")
        
        if metadata.author:
            lines.append(f"author: {metadata.author}")
        
        if metadata.publication_date:
            lines.append(f"date: {metadata.publication_date}")
        
        if metadata.isbn:
            lines.append(f"isbn: {metadata.isbn}")
        
        lines.append(f"language: {language}")
        lines.append(f"generated: {datetime.utcnow().isoformat()}")
        lines.append("---")
        
        return "\n".join(lines)
    
    def _generate_title_page(self, metadata: BookMetadata) -> str:
        """Generate title page."""
        lines = [f"# {metadata.title}"]
        
        if metadata.author:
            lines.append(f"**Author:** {metadata.author}")
        
        if metadata.publication_date:
            lines.append(f"**Published:** {metadata.publication_date}")
        
        if metadata.isbn:
            lines.append(f"**ISBN:** {metadata.isbn}")
        
        return "\n\n".join(lines)
    
    def _generate_toc(self, sections: List[SectionInfo]) -> str:
        """Generate table of contents from sections."""
        lines = ["## Table of Contents\n"]
        
        for section in sections:
            # Indent based on level
            indent = "  " * (section.level - 1)
            
            # Create TOC entry with page range
            entry = f"{indent}- {section.title} (Pages {section.page_start}-{section.page_end})"
            lines.append(entry)
        
        return "\n".join(lines)
    
    def _generate_toc_from_chunks(self, chunks: List[ChunkInfo]) -> str:
        """Generate TOC from chunks (unique sections only)."""
        lines = ["## Table of Contents\n"]
        seen_sections = set()
        
        for chunk in chunks:
            if chunk.section_id not in seen_sections:
                entry = f"- {chunk.section_title} (Pages {chunk.page_start}-{chunk.page_end})"
                lines.append(entry)
                seen_sections.add(chunk.section_id)
        
        return "\n".join(lines)
    
    def _generate_section(
        self, 
        section: SectionInfo, 
        pages: List[PageInfo],
        language: str
    ) -> str:
        """Generate Markdown for a single section."""
        # Section header (level based on TOC hierarchy)
        header_level = "#" * (section.level + 1)  # +1 because title is H1
        lines = [f"{header_level} {section.title}"]
        
        # Add page range annotation
        lines.append(f"*Pages {section.page_start}-{section.page_end}*\n")
        
        # Get section content
        section_pages = [
            p for p in pages 
            if section.page_start <= p.page <= section.page_end
        ]
        
        # Join page content
        for page in section_pages:
            if page.has_text and page.text:
                # Clean and format text
                text = self._clean_text(page.text, language)
                lines.append(text)
        
        return "\n\n".join(lines)
    
    def _clean_text(self, text: str, language: str) -> str:
        """
        Clean and format extracted text.
        
        - Remove excessive whitespace
        - Fix common OCR issues
        - Preserve paragraph structure
        """
        # Split into paragraphs
        paragraphs = text.split("\n\n")
        
        cleaned = []
        for para in paragraphs:
            # Remove excessive whitespace within paragraphs
            para = " ".join(para.split())
            
            # Skip very short paragraphs (likely artifacts)
            if len(para.strip()) < 10:
                continue
            
            cleaned.append(para)
        
        return "\n\n".join(cleaned)
    
    def save_to_file(self, content: str, output_path: str) -> None:
        """Save Markdown content to file."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Saved Markdown to {output_path}")