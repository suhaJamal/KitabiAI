# app/services/arabic_toc_extractor.py
"""
Arabic-specific TOC extraction using pre-extracted text from Azure.

This module handles Table of Contents (TOC) extraction from Arabic PDF books.
It uses text that was already extracted by Azure Document Intelligence during
the language detection phase, avoiding redundant API calls.

Key Features:
- Detects TOC at beginning OR end of book (common in Arabic publishing)
- Uses Arabic synonyms for "Table of Contents" header detection
- Handles separate-line format: title on one line, page number on next line
- Filters out headers, footers, and page breaks
- Validates page number sequences to detect body text contamination

Author: Suha Islaih
Date: October 2025
"""

import re
import logging
from typing import List, Optional

from ..models.schemas import SectionInfo, SectionsReport


logger = logging.getLogger(__name__)


class ArabicTocExtractor:
    """
    Extract Table of Contents from Arabic text pre-extracted by Azure.
    
    This class handles the unique challenges of Arabic PDF books:
    - TOC can be at the beginning OR end of the book
    - Title and page number are typically on separate lines
    - Arabic and Western-Arabic digits (٠-٩) need normalization
    - Headers, footers, and page breaks need filtering
    
    The extraction process:
    1. Search for TOC header using Arabic patterns
    2. Extract text segment (generous, let parsing filter)
    3. Parse title-page pairs
    4. Clean entries (validate page number sequences)
    5. Create SectionInfo objects with page ranges
    """
    
    # Arabic synonyms for "Table of Contents"
    # These are the most common ways Arabic books title their TOC
    TOC_PATTERNS = [
        r"المحتويات",              # "Contents" - most common
        r"فهرس",                   # "Index/Contents"
        r"فهرس\s+المحتويات",      # "Index of Contents"
        r"جدول\s+المحتويات",      # "Table of Contents"
        r"فهرس\s+الموضوعات",      # "Index of Topics"
        r"جدول\s+الموضوعات"       # "Table of Topics"
    ]
    
    def __init__(self):
        """Initialize the Arabic TOC extractor with compiled regex patterns."""
        # Compile all TOC header patterns into a single regex for efficiency
        self.toc_regex = re.compile("|".join(self.TOC_PATTERNS))

    def extract(self, extracted_text: str) -> SectionsReport:
        """
        Extract TOC from pre-extracted Arabic text.
        
        Strategy:
        1. Try to find TOC at beginning of book (first 33% of text)
        2. If not found or insufficient entries, try end of book (last 20%)
        3. If still not found, return fallback single section
        
        Args:
            extracted_text: Full text already extracted from PDF via Azure
        
        Returns:
            SectionsReport containing list of extracted sections with page ranges
        """
        logger.info("Starting Arabic TOC extraction from pre-extracted text")
        
        if not extracted_text:
            logger.warning("No text provided. Returning fallback section.")
            return self._fallback_section()
        
        # Step 1: Try beginning of book (first third)
        toc_text = self._extract_toc_segment(
            extracted_text[:len(extracted_text)//3], 
            "beginning"
        )
        
        if toc_text:
            entries = self._parse_toc_entries(toc_text)
            entries = self._clean_entries(entries)  # Validate page sequences
            
            # Require at least 5 valid entries to accept TOC
            # This prevents false positives from copyright pages, etc.
            if len(entries) >= 5:
                sections = self._create_sections(entries)
                logger.info(f"✅ Found valid TOC at beginning with {len(sections)} sections")
                return SectionsReport(bookmarks_found=True, sections=sections)
            else:
                logger.warning(
                    f"Found header at beginning but only {len(entries)} valid "
                    f"entries after cleaning. Trying end..."
                )
        
        # Step 2: Try end of book (last 20%)
        logger.info("Searching for TOC at end of book...")
        end_portion = extracted_text[int(len(extracted_text)*0.8):]
        toc_text = self._extract_toc_segment(end_portion, "end")
        
        if toc_text:
            entries = self._parse_toc_entries(toc_text)
            entries = self._clean_entries(entries)
            
            if len(entries) >= 5:
                sections = self._create_sections(entries)
                logger.info(f"✅ Found valid TOC at end with {len(sections)} sections")
                return SectionsReport(bookmarks_found=True, sections=sections)
        
        # Step 3: No valid TOC found anywhere
        logger.warning("No valid TOC found anywhere. Returning fallback section.")
        return self._fallback_section()

    def _extract_toc_segment(self, text_part: str, context_label: str) -> Optional[str]:
        """
        Extract TOC segment from text using generous extraction strategy.
        
        Instead of trying to detect exactly where TOC ends (which is error-prone
        due to page breaks, headers, footers), we extract generously and rely
        on the parsing and validation phases to filter out noise.
        
        Strategy:
        - At beginning: Take first 200 lines (covers multi-page TOCs)
        - At end: Take everything (it's all TOC until end of book)
        
        Args:
            text_part: Portion of book text to search (beginning or end)
            context_label: "beginning" or "end" for logging
        
        Returns:
            Extracted TOC text as string, or None if TOC header not found
        """
        logger.info(f"Searching for TOC in {context_label} section...")
        
        # Search for TOC header using compiled regex
        toc_header_match = self.toc_regex.search(text_part)
        if not toc_header_match:
            return None
        
        header_text = toc_header_match.group().strip()
        toc_start = toc_header_match.start()
        logger.info(f"TOC header detected: '{header_text}' in {context_label}")
        
        # Extract all lines after the TOC header
        sample_after_header = text_part[toc_start:]
        lines = [l.strip() for l in sample_after_header.split("\n") if l.strip()]
        
        # Skip duplicate headers (sometimes TOC header appears multiple times)
        skip_words = ["المحتويات", "فهرس", "فهرس المحتويات", "جدول المحتويات"]
        filtered = [l for l in lines[1:] if not any(sw in l for sw in skip_words)]
        
        # Apply generous extraction based on location
        if context_label == "end":
            # At end: take everything (it's all TOC until end of book)
            toc_entries = filtered
            logger.info(f"TOC at end - taking all {len(toc_entries)} lines")
        else:
            # At beginning: take first 200 lines (covers even long multi-page TOCs)
            # This ensures we don't miss any TOC entries due to page breaks
            toc_entries = filtered[:200]
            logger.info(f"TOC at beginning - taking first {len(toc_entries)} lines (max 200)")
        
        if not toc_entries:
            logger.warning("No TOC entries found")
            return None
        
        toc_text = "\n".join(toc_entries)
        logger.info(f"Extracted {len(toc_entries)} lines for parsing")
        return toc_text

    def _parse_toc_entries(self, toc_text: str) -> List[dict]:
        """
        Parse TOC text into title-page pairs supporting multiple formats.

        Arabic TOC Formats (after Azure extraction):
        Format A (same line): "Title PageNumber" (e.g., "تمهيد السلسلة 9")
        Format B (separate lines):
          Line 1: Title (e.g., "الفصل الأول")
          Line 2: Page number (e.g., "5" or "٥")

        Process:
        1. Filter out headers/footers (but keep page numbers in TOC context)
        2. Try Format A first (same line): split by last space to separate title from page
        3. Fall back to Format B (separate lines): pair consecutive lines
        4. Normalize Arabic-Indic digits (٠-٩) to Western (0-9)
        5. Validate each entry (title must have text, page must be valid number)
        6. Keep chapter numbers in titles (e.g., "١ - أيتها المرآة على الحائط")

        Args:
            toc_text: Raw TOC text segment

        Returns:
            List of dicts with 'title' and 'page' keys
        """
        lines = [l.strip() for l in toc_text.split("\n") if l.strip()]

        # Log raw lines BEFORE filtering (for debugging)
        logger.info(f"Raw lines BEFORE filtering: {len(lines)}")
        logger.info(f"First 10 raw lines:")
        for i, line in enumerate(lines[:10], 1):
            logger.info(f"  RAW {i}. [{line}]")

        # Filter out headers/footers but KEEP page numbers
        # in_toc_context=True tells filter to be lenient with small numbers
        filtered_lines = []
        filtered_count = 0
        for l in lines:
            if self._is_header_footer(l, in_toc_context=True):
                logger.info(f"FILTERED OUT: [{l}]")  # Changed to INFO to debug missing "9"
                filtered_count += 1
            else:
                filtered_lines.append(l)

        lines = filtered_lines
        logger.info(f"After filtering: {len(lines)} lines (filtered out: {filtered_count})")

        # Log first 30 lines for debugging purposes
        logger.info(f"First 30 lines:")
        for i, line in enumerate(lines[:30], 1):
            logger.info(f"  {i}. [{line}]")

        def normalize_digits(s: str) -> str:
            """Convert Arabic-Indic digits (٠-٩) to Western digits (0-9)."""
            return s.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))

        entries = []
        i = 0

        # Process lines supporting both formats
        while i < len(lines):
            current_line = lines[i]

            # Format A: Try same-line format first (e.g., "تمهيد السلسلة 9")
            # Split by last space and check if last part is a page number
            parts = current_line.rsplit(None, 1)  # Split by last whitespace
            if len(parts) == 2:
                potential_title, potential_page = parts
                normalized_page = normalize_digits(potential_page)

                # Check if last part is ONLY digits
                if re.fullmatch(r'\d+', normalized_page):
                    try:
                        page_num = int(normalized_page)
                        # Sanity check: page number should be reasonable (1-9999)
                        if 1 <= page_num <= 9999:
                            # Valid same-line format
                            title = potential_title.strip()
                            # Keep chapter numbers - don't remove them!
                            entries.append({"title": title, "page": page_num})
                            logger.info(f"✅ ENTRY {len(entries)} (same-line): '{title}' -> {page_num}")
                            i += 1  # Move to next line
                            continue
                    except ValueError:
                        pass

            # Format B: Try separate-line format (next line is page number)
            if i < len(lines) - 1:
                title_line = current_line
                page_line = lines[i + 1]

                # Keep chapter numbers - don't remove them!
                title = title_line.strip()

                # Check if next line is ONLY a page number (no other text)
                normalized_page_line = normalize_digits(page_line)
                if re.fullmatch(r'\d+', normalized_page_line):
                    # Validate: title must not be empty and not be just a number itself
                    if title and not re.fullmatch(r'[\u0660-\u0669\d]+', title):
                        try:
                            page_num = int(normalized_page_line)
                            # Sanity check: page number should be reasonable (1-9999)
                            if 1 <= page_num <= 9999:
                                entries.append({"title": title, "page": page_num})
                                logger.info(f"✅ ENTRY {len(entries)} (separate-line): '{title}' -> {page_num}")
                                i += 2  # Skip both title and page lines
                                continue
                        except ValueError:
                            pass

            # If neither format matched, move to next line
            i += 1

        logger.info(f"✅ Parsed {len(entries)} valid TOC entries")
        return entries

    def _create_sections(self, entries: List[dict]) -> List[SectionInfo]:
        """
        Convert parsed entries into SectionInfo objects with page ranges.
        
        Each section's end page is calculated as (next section's start page - 1).
        For the last section, we set a placeholder (start + 100) which will be
        corrected by the caller based on the actual PDF page count.
        
        Args:
            entries: List of dicts with 'title' and 'page' keys
        
        Returns:
            List of SectionInfo objects with hierarchical IDs and page ranges
        """
        sections = []
        
        for idx, entry in enumerate(entries):
            page_start = entry["page"]
            
            # Calculate page_end: until next section starts
            if idx + 1 < len(entries):
                page_end = entries[idx + 1]["page"] - 1
            else:
                # Last section: set placeholder that caller will fix
                page_end = page_start + 100
            
            # Ensure page_end is never less than page_start
            page_end = max(page_start, page_end)
            
            sections.append(
                SectionInfo(
                    section_id=str(idx + 1),  # Simple sequential IDs: 1, 2, 3...
                    title=entry["title"],
                    level=1,  # Arabic TOCs typically don't have hierarchy
                    page_start=page_start,
                    page_end=page_end
                )
            )
        
        return sections
    
    def _fallback_section(self) -> SectionsReport:
        """
        Return a single fallback section when TOC extraction fails.
        
        This provides a graceful degradation: instead of failing completely,
        we return a single section spanning the entire document.
        
        Returns:
            SectionsReport with one section covering the whole document
        """
        return SectionsReport(
            bookmarks_found=False,
            sections=[
                SectionInfo(
                    section_id="1",
                    title="Document",
                    level=1,
                    page_start=1,
                    page_end=9999  # Placeholder, will be fixed by caller
                )
            ]
        )
    
    def _is_header_footer(self, line: str, in_toc_context: bool = False) -> bool:
        """
        Detect and filter out header/footer patterns.
        
        Context-aware filtering:
        - In TOC context: Be lenient with numbers (they're page numbers we need!)
        - Outside TOC: Be aggressive (filter lone numbers, page markers, etc.)
        
        Common patterns filtered:
        - Timestamps: "10/20/20 9:10 AM"
        - InDesign footers: "filename.indd 223"
        - Copyright symbols: "©"
        - Page markers: "صفحة 5", "page 5"
        - ISBN/publication info
        
        Args:
            line: Text line to check
            in_toc_context: If True, be lenient with small numbers
        
        Returns:
            True if line should be filtered out, False to keep
        """
        line = line.strip()
        
        # Define patterns based on context
        if in_toc_context:
            # In TOC: Only filter obvious non-TOC patterns
            # KEEP small numbers (they're page numbers!)
            patterns = [
                r'^\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}',  # Timestamps
                r'^[\w\s]+\.indd\s+\d+$',                      # InDesign footers
                r'^©',                                          # Copyright
            ]
        else:
            # Outside TOC: Filter aggressively
            patterns = [
                r'^\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}',  # Timestamps
                r'^[\w\s]+\.indd\s+\d+$',                      # InDesign footers
                r'^صفحة\s*\d+$',                               # "Page 5" in Arabic
                r'^ص\s*[\u0660-\u0669\d]+$',                   # "ص ٥" abbreviation
                r'^\d+\s*$',                                   # Lone page numbers
                r'^[\u0660-\u0669]+\s*$',                      # Arabic digits alone
                r'^page\s+\d+$',                               # "page 5" in English
                r'^الطبعة',                                    # Edition info
                r'^©',                                          # Copyright
                r'^\d{4}هـ',                                   # Hijri year
                r'^\d{4}م',                                    # Gregorian year
                r'^ISBN',                                      # ISBN
                r'^ردمك',                                      # ISBN in Arabic
            ]
        
        # Check against all patterns
        for pattern in patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True

        # Filter very short lines (likely decorative or noise)
        # BUT: In TOC context, keep single digits (they're page numbers like "9" or "٩")
        if len(line) < 2:
            if in_toc_context and re.fullmatch(r'[\u0660-\u0669\d]', line):
                # Single digit in TOC = page number, keep it!
                return False
            else:
                # Other short lines = noise, filter them
                return True

        # Filter lines with only special characters (decorative elements)
        if re.match(r'^[\W_]+$', line):
            return True

        return False
    
    def _clean_entries(self, entries: List[dict]) -> List[dict]:
        """
        Validate and clean TOC entries by checking page number sequences.
        
        Problem: When we extract generously, we sometimes capture body text
        after the real TOC ends. Body text often has page numbers that don't
        follow the TOC's sequential pattern.
        
        Detection Strategy:
        1. Page numbers should increase monotonically (or stay same for sub-sections)
        2. Backward jumps indicate contamination from another part of the book
        3. Large backward jumps (e.g., 147 → 14) are definitely body text
        4. Small numbers after large ones (e.g., 147 → 15) suggest page reset
        
        Args:
            entries: List of parsed TOC entries
        
        Returns:
            Cleaned list with invalid entries removed
        """
        if not entries:
            return entries
        
        clean = []
        prev_page = 0
        
        for entry in entries:
            current_page = entry["page"]
            
            # Check 1: Page numbers must not go backward
            if current_page < prev_page:
                logger.warning(
                    f"Page went backward: {prev_page} -> {current_page}. "
                    f"Stopping TOC extraction."
                )
                break
            
            # Check 2: Detect large backward jumps (body text contamination)
            if prev_page > 0 and current_page < prev_page - 5:
                logger.warning(
                    f"Large backward jump: {prev_page} -> {current_page}. Stopping."
                )
                break
            
            # Check 3: Detect suspicious resets (large page → small page)
            # Example: TOC ends at page 147, then body text has page 14
            if prev_page > 100 and current_page < 50:
                logger.warning(
                    f"Suspicious reset: {prev_page} -> {current_page}. Stopping."
                )
                break
            
            # Entry passed all checks
            clean.append(entry)
            prev_page = current_page
        
        logger.info(f"Cleaned: {len(entries)} -> {len(clean)} entries")
        return clean