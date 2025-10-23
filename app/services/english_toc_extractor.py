# app/services/english_toc_extractor.py
"""
Pattern-based TOC extraction for English PDFs without native bookmarks.

Extracts chapter/section headings using common English patterns:
- "Chapter N: Title"
- "N. Title" 
- "Section N: Title"
- Numbered headings with various formats
"""

import re
import logging
from typing import List, Optional
from ..models.schemas import SectionInfo, SectionsReport


logger = logging.getLogger(__name__)


class EnglishTocExtractor:
    """Extract TOC from English PDF text using pattern matching."""
    
    # Common English TOC patterns
    PATTERNS = [
        # Chapter 1: Introduction
        # Chapter 1 - Introduction  
        # Chapter 1. Introduction
        r'^(Chapter\s+(\d+)[\s:.–-]+(.+))$',
        
        # CHAPTER 1: INTRODUCTION (all caps)
        r'^(CHAPTER\s+(\d+)[\s:.–-]+(.+))$',
        
        # 1. Introduction
        # 1.1 Background
        # 1.1.1 History
        r'^((\d+(?:\.\d+)*)\s*[\s:.–-]\s*(.+))$',
        
        # Section 1: Introduction
        # Section 1.1: Background
        r'^(Section\s+(\d+(?:\.\d+)*)\s*[\s:.–-]\s*(.+))$',
        
        # Part I: Introduction
        # Part 1: Introduction
        r'^(Part\s+([IVXLCDM\d]+)[\s:.–-]+(.+))$',
        
        # Appendix A: Details
        r'^(Appendix\s+([A-Z\d]+)[\s:.–-]+(.+))$',
    ]
    
    def __init__(self, min_sections: int = 3):
        """
        Args:
            min_sections: Minimum number of sections to consider extraction successful
        """
        self.min_sections = min_sections
        self.compiled_patterns = [re.compile(p, re.MULTILINE | re.IGNORECASE) 
                                  for p in self.PATTERNS]
    
    def extract(self, text: str, num_pages: int) -> SectionsReport:
        """
        Extract TOC from English text using pattern matching.
        
        Args:
            text: Full text extracted from PDF
            num_pages: Total number of pages in PDF
            
        Returns:
            SectionsReport with extracted sections or fallback
        """
        sections = self._extract_sections(text, num_pages)
        
        if len(sections) >= self.min_sections:
            logger.info(f"Pattern-based extraction found {len(sections)} sections")
            return SectionsReport(bookmarks_found=False, sections=sections)
        
        logger.info(f"Insufficient sections found ({len(sections)}), using fallback")
        return SectionsReport(
            bookmarks_found=False,
            sections=[
                SectionInfo(
                    section_id="1",
                    title="Document",
                    level=1,
                    page_start=1,
                    page_end=num_pages
                )
            ]
        )
    
    def _extract_sections(self, text: str, num_pages: int) -> List[SectionInfo]:
        """Extract sections using pattern matching."""
        matches = []
        
        # Try each pattern
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                full_text = match.group(1).strip()
                number = match.group(2).strip()
                title = match.group(3).strip()
                
                # Skip if title is too short or looks like noise
                if len(title) < 3 or len(title) > 200:
                    continue
                
                # Estimate page number from text position
                char_pos = match.start()
                estimated_page = max(1, min(num_pages, 
                                           int((char_pos / len(text)) * num_pages) + 1))
                
                matches.append({
                    'number': number,
                    'title': title,
                    'page': estimated_page,
                    'full': full_text
                })
        
        if not matches:
            return []
        
        # Remove duplicates (keep first occurrence)
        seen = set()
        unique_matches = []
        for m in matches:
            key = (m['number'], m['title'][:50])  # Use truncated title as key
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)
        
        # Sort by page and number
        unique_matches.sort(key=lambda x: (x['page'], self._parse_section_number(x['number'])))
        
        # Convert to SectionInfo
        sections = []
        for i, match in enumerate(unique_matches):
            # Determine level based on number format
            level = self._determine_level(match['number'])
            
            # Determine page range
            page_start = match['page']
            page_end = unique_matches[i + 1]['page'] - 1 if i + 1 < len(unique_matches) else num_pages
            page_end = max(page_start, page_end)
            
            sections.append(
                SectionInfo(
                    section_id=match['number'],
                    title=match['title'],
                    level=level,
                    page_start=page_start,
                    page_end=page_end
                )
            )
        
        return sections
    
    def _determine_level(self, number: str) -> int:
        """
        Determine hierarchical level from section number.
        
        Examples:
            "1" -> level 1
            "1.1" -> level 2
            "1.1.1" -> level 3
            "I" -> level 1
            "A" -> level 1
        """
        # Count dots in number
        if '.' in number:
            return number.count('.') + 1
        return 1
    
    def _parse_section_number(self, number: str) -> tuple:
        """
        Parse section number into sortable tuple.
        
        Examples:
            "1" -> (1,)
            "1.2" -> (1, 2)
            "1.10.3" -> (1, 10, 3)
        """
        try:
            return tuple(int(n) for n in number.split('.'))
        except ValueError:
            # If not numeric (e.g., Roman numerals or letters), return as is
            return (0,)