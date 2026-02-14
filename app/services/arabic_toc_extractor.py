# app/services/arabic_toc_extractor.py
"""
Arabic-specific TOC extraction with hybrid approach (table + text-based).

This module handles Table of Contents (TOC) extraction from Arabic PDF books.
It supports multiple extraction strategies:
1. Azure table-based extraction (when page hint provided)
2. Text-based pattern matching at beginning of book
3. Text-based pattern matching at end of book
4. Fallback to single section

Copied from arabic-books-engine/extractors/arabic_toc_extractor.py
with import path adjustments for the original project structure.

Author: Suha Islaih
Date: October 2025
"""

import re
import json
import os
import logging
from datetime import datetime
from typing import List, Optional, Any

from ..models.schemas import SectionInfo, SectionsReport


logger = logging.getLogger(__name__)

# Evaluation log directory
EVAL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'evaluation')


class ArabicTocExtractor:
    """
    Extract Table of Contents from Arabic PDFs using hybrid approach.

    Strategies (in order):
    1. Azure table-based extraction (if page hint provided)
    2. Text-based search at beginning (first 33%)
    3. Text-based search at end (last 20%)
    4. Fallback to single section

    Handles:
    - Multi-column TOC layouts (4-column and 2-column tables)
    - Arabic-Indic digits (٠-٩) normalization
    - Page offset between book page numbers and PDF page numbers
    - Separate-line format (title on one line, page number on next)
    """

    # Arabic synonyms for "Table of Contents"
    # Note: Keep lenient matching (e.g., "فهرس" matches "فهرسة" too)
    # False positives are filtered by validation logic in _extract_toc_segment()
    TOC_PATTERNS = [
        r"المحتويات",              # "Contents" - most common
        r"فهرس",                   # "Index/Contents" (matches "فهرسة" too - validated later)
        r"فهرس\s+المحتويات",      # "Index of Contents"
        r"جدول\s+المحتويات",      # "Table of Contents"
        r"فهرس\s+الموضوعات",      # "Index of Topics"
        r"جدول\s+الموضوعات",       # "Table of Topics"
        r"^محتويات الكتاب$"       # "Table of Topics"
    ]

    def __init__(self):
        """Initialize the Arabic TOC extractor with compiled regex patterns."""
        # Compile all TOC header patterns into a single regex for efficiency
        self.toc_regex = re.compile("|".join(self.TOC_PATTERNS))

    def extract(
        self,
        extracted_text: str,
        toc_page_number: Optional[int] = None,
        azure_result: Optional[Any] = None,
        page_offset: int = 0,
        book_title: str = "unknown"
    ) -> SectionsReport:
        """
        Extract TOC from pre-extracted Arabic text with hybrid approach.

        Strategy (Hybrid):
        1. If toc_page_number provided and azure_result available, try table-based extraction
        2. Fall back to text-based search at beginning of book (first 33% of text)
        3. If not found or insufficient entries, try end of book (last 20%)
        4. If still not found, return fallback single section

        Args:
            extracted_text: Full text already extracted from PDF via Azure
            toc_page_number: Optional page number where TOC is located (user hint)
            azure_result: Optional full Azure result object (includes tables, paragraphs)
            page_offset: Offset to add to book page numbers to get PDF page numbers (default: 0)
                        Example: if book page 1 is on PDF page 15, offset = 14
            book_title: Book title for evaluation logging

        Returns:
            SectionsReport containing list of extracted sections with page ranges
        """
        logger.info("Starting Arabic TOC extraction (hybrid approach)")

        eval_data = {
            'book_title': book_title,
            'method': 'extract_arabic',
            'timestamp': datetime.now().isoformat(),
            'toc_page_provided': toc_page_number,
            'page_offset': page_offset,
            'strategy_used': None,
            'entries_before_clean': 0,
            'entries_after_clean': 0,
            'sections_created': 0,
            'final_sections': []
        }

        if not extracted_text:
            logger.warning("No text provided. Returning fallback section.")
            eval_data['strategy_used'] = 'fallback_no_text'
            self._write_eval_log(eval_data)
            return self._fallback_section()

        # Step 1: Try Azure table-based extraction (if page hint provided)
        if toc_page_number and azure_result:
            logger.info(f"Trying Azure table extraction on page {toc_page_number} (page offset: {page_offset})")
            sections = self._extract_from_table(toc_page_number, azure_result, page_offset)
            if sections:
                logger.info(f"✅ Found valid TOC from Azure table with {len(sections)} sections")
                eval_data['strategy_used'] = 'azure_table'
                eval_data['sections_created'] = len(sections)
                eval_data['final_sections'] = [
                    {'title': s.title, 'page_start': s.page_start, 'page_end': s.page_end, 'level': s.level}
                    for s in sections
                ]
                self._write_eval_log(eval_data)
                return SectionsReport(bookmarks_found=True, sections=sections)
            else:
                logger.info("No valid table found, falling back to text-based search")

        # Step 2: Try beginning of book (first third)
        toc_text = self._extract_toc_segment(
            extracted_text[:len(extracted_text)//3],
            "beginning"
        )

        if toc_text:
            entries = self._parse_toc_entries(toc_text)
            raw_count = len(entries)
            entries = self._clean_entries(entries)  # Validate page sequences

            # Require at least 5 valid entries to accept TOC
            # This prevents false positives from copyright pages, etc.
            if len(entries) >= 5:
                sections = self._create_sections(entries, page_offset)
                logger.info(f"✅ Found valid TOC at beginning with {len(sections)} sections")
                eval_data['strategy_used'] = 'text_beginning'
                eval_data['entries_before_clean'] = raw_count
                eval_data['entries_after_clean'] = len(entries)
                eval_data['sections_created'] = len(sections)
                eval_data['final_sections'] = [
                    {'title': s.title, 'page_start': s.page_start, 'page_end': s.page_end, 'level': s.level}
                    for s in sections
                ]
                self._write_eval_log(eval_data)
                return SectionsReport(bookmarks_found=True, sections=sections)
            else:
                logger.warning(
                    f"Found header at beginning but only {len(entries)} valid "
                    f"entries after cleaning. Trying end..."
                )

        # Step 3: Try end of book (last 20%)
        end_portion = extracted_text[int(len(extracted_text)*0.8):]
        toc_text = self._extract_toc_segment(end_portion, "end")

        if toc_text:
            entries = self._parse_toc_entries(toc_text)
            raw_count = len(entries)
            entries = self._clean_entries(entries)

            if len(entries) >= 5:
                sections = self._create_sections(entries, page_offset)
                logger.info(f"✅ Found valid TOC at end with {len(sections)} sections")
                eval_data['strategy_used'] = 'text_end'
                eval_data['entries_before_clean'] = raw_count
                eval_data['entries_after_clean'] = len(entries)
                eval_data['sections_created'] = len(sections)
                eval_data['final_sections'] = [
                    {'title': s.title, 'page_start': s.page_start, 'page_end': s.page_end, 'level': s.level}
                    for s in sections
                ]
                self._write_eval_log(eval_data)
                return SectionsReport(bookmarks_found=True, sections=sections)

        # Step 4: No valid TOC found anywhere
        logger.warning("No valid TOC found anywhere. Returning fallback section.")
        eval_data['strategy_used'] = 'fallback_none_found'
        self._write_eval_log(eval_data)
        return self._fallback_section()

    def _extract_from_table(self, page_number: int, azure_result: Any, page_offset: int = 0, max_pages: int = 20) -> Optional[List[SectionInfo]]:
        """
        Extract TOC from Azure-detected tables starting from specified page.

        Handles multi-page TOCs by checking consecutive pages for continuation.
        Handles multi-column TOC layouts:
        - 4-column table: [Title1, Page1, Title2, Page2]
        - 2-column table: [Title, Page]

        Args:
            page_number: Starting page number where TOC is located
            azure_result: Full Azure Document Intelligence result object
            page_offset: Offset to add to book page numbers to get PDF page numbers (default: 0)
            max_pages: Maximum number of consecutive pages to check (default: 20)

        Returns:
            List of SectionInfo objects, or None if no valid table found
        """
        # Check if tables exist in Azure result
        if not hasattr(azure_result, 'tables') or not azure_result.tables:
            logger.info("No tables found in Azure result")
            return None

        # Find ALL tables on the specified page AND following consecutive pages
        # This handles multi-page TOCs (e.g., TOC spanning pages 345-349)
        page_tables = []
        total_pages = len(azure_result.pages)

        for page_offset_check in range(max_pages):
            current_page = page_number + page_offset_check

            # Stop if we exceed the document page count
            if current_page > total_pages:
                break

            # Find tables on this page
            tables_on_page = [
                t for t in azure_result.tables
                if t.bounding_regions and t.bounding_regions[0].page_number == current_page
            ]

            # If we find tables on this page, add them
            if tables_on_page:
                logger.info(f"Found {len(tables_on_page)} table(s) on page {current_page}")
                page_tables.extend(tables_on_page)
            # If this is NOT the first page and we find no tables, stop searching
            # (TOC has ended)
            elif page_offset_check > 0:
                logger.info(f"No tables on page {current_page}, TOC ends at page {current_page - 1}")
                break

        if not page_tables:
            logger.info(f"No tables found starting from page {page_number}")
            return None

        logger.info(f"Processing {len(page_tables)} table(s) across {page_offset_check + 1} page(s)")

        # Collect ALL entries from ALL tables across all pages
        all_entries = []

        for table_idx, table in enumerate(page_tables):
            table_page = table.bounding_regions[0].page_number if table.bounding_regions else "unknown"
            logger.info(f"Analyzing table #{table_idx + 1} on page {table_page}: {table.row_count} rows × {table.column_count} columns")

            # Handle 4-column table (two-column TOC layout)
            if table.column_count == 4:
                logger.info("Detected 4-column table (two-column TOC layout)")
                for cell in table.cells:
                    row = cell.row_index
                    col = cell.column_index
                    content = cell.content.strip()

                    # Page number columns (1 and 3)
                    if col in [1, 3]:
                        # Get the title from previous column
                        title_col = col - 1
                        title_cell = next(
                            (c for c in table.cells
                             if c.row_index == row and c.column_index == title_col),
                            None
                        )

                        if title_cell and content:
                            title = title_cell.content.strip()
                            # Normalize Arabic-Indic digits
                            normalized_page = self._normalize_arabic_digits(content)

                            # Handle "و" (and) - take only first number
                            # Example: "٣ و ٢٥٧" -> take "3", ignore "257"
                            if 'و' in normalized_page or ' و ' in normalized_page:
                                normalized_page = normalized_page.split('و')[0].strip()

                            if title and normalized_page.isdigit():
                                page_num = int(normalized_page)
                                if 1 <= page_num <= 9999:
                                    all_entries.append({"title": title, "page": page_num})

            # Handle 2-column table (single-column TOC layout)
            elif table.column_count == 2:
                logger.info("Detected 2-column table (single-column TOC layout)")
                for cell in table.cells:
                    row = cell.row_index
                    col = cell.column_index
                    content = cell.content.strip()

                    # Page number column (1)
                    if col == 1:
                        title_cell = next(
                            (c for c in table.cells
                             if c.row_index == row and c.column_index == 0),
                            None
                        )

                        if title_cell and content:
                            title = title_cell.content.strip()
                            normalized_page = self._normalize_arabic_digits(content)

                            # Handle "و" (and) - take only first number
                            # Example: "٣ و ٢٥٧" -> take "3", ignore "257"
                            if 'و' in normalized_page or ' و ' in normalized_page:
                                normalized_page = normalized_page.split('و')[0].strip()

                            if title and normalized_page.isdigit():
                                page_num = int(normalized_page)
                                if 1 <= page_num <= 9999:
                                    all_entries.append({"title": title, "page": page_num})

        logger.info(f"Extracted {len(all_entries)} total entries from all tables")

        # Process all entries together
        if len(all_entries) >= 5:
            # IMPORTANT: Sort entries by page number first!
            # Multi-column tables will have non-sequential page numbers
            # Also, entries from multiple pages need to be in order
            entries_sorted = sorted(all_entries, key=lambda x: x["page"])
            logger.info(f"Sorted {len(entries_sorted)} entries by page number (first: {entries_sorted[0]['page']}, last: {entries_sorted[-1]['page']})")

            # Clean and validate entries
            entries_clean = self._clean_entries(entries_sorted)
            if len(entries_clean) >= 5:
                sections = self._create_sections(entries_clean, page_offset)
                logger.info(f"✅ Created {len(sections)} sections from multi-page TOC (with offset {page_offset})")
                return sections
            else:
                logger.warning(f"Only {len(entries_clean)} entries after cleaning")

        logger.info("No valid table with sufficient entries found")
        return None

    def _normalize_arabic_digits(self, text: str) -> str:
        """
        Normalize Arabic-Indic digits (٠-٩) to Western digits (0-9).

        Args:
            text: Text containing Arabic-Indic digits

        Returns:
            Text with normalized digits
        """
        arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        return text.translate(arabic_to_western)

    def _extract_toc_segment(self, text_part: str, context_label: str) -> Optional[str]:
        """
        Extract TOC segment from text using generous extraction strategy.

        Instead of trying to detect exactly where TOC ends (which is error-prone
        due to page breaks, headers, footers), we extract generously and rely
        on the parsing and validation phases to filter out noise.

        Args:
            text_part: Text segment to search (beginning or end portion)
            context_label: "beginning" or "end" (for logging)

        Returns:
            TOC text segment if found, None otherwise
        """
        match = self.toc_regex.search(text_part)

        if not match:
            logger.info(f"No TOC header found at {context_label}")
            return None

        # Validate the header is actually a TOC header (not part of a sentence)
        # Get surrounding context (20 chars before and after)
        start_pos = max(0, match.start() - 20)
        end_pos = min(len(text_part), match.end() + 20)
        context = text_part[start_pos:end_pos]

        # Check for invalidating patterns that indicate this is NOT a TOC header
        # For example: "فهرسة" (indexing/cataloging) should be rejected if it's
        # part of a sentence like "فهرسة الكتب" (cataloging books)
        if "فهرسة" in match.group():
            # "فهرسة" can mean "indexing/cataloging" (false positive)
            # vs "فهرس" which means "table of contents"
            # Reject if followed by non-TOC words
            if re.search(r"فهرسة\s+(الكتب|المراجع|البيانات)", context):
                logger.info(
                    f"Rejected false positive at {context_label}: '{match.group()}' "
                    f"in context '{context.strip()}'"
                )
                return None

        # Validate: header should be on its own line or followed by newline
        # (not in the middle of a paragraph)
        if match.start() > 0 and text_part[match.start() - 1] not in ['\n', '\f']:
            # Not at start of line, likely false positive
            logger.info(f"Rejected header not at line start: '{context.strip()}'")
            return None

        logger.info(f"✅ Found TOC header at {context_label}: '{match.group()}'")

        # Extract generously: from header to end of this text segment
        # Let parsing and validation filter out non-TOC content
        toc_segment = text_part[match.start():]

        logger.info(
            f"Extracted TOC segment ({len(toc_segment)} chars) "
            f"from {context_label}"
        )

        return toc_segment

    def _parse_toc_entries(self, toc_text: str) -> List[dict]:
        """
        Parse TOC entries from text.

        Handles the common Arabic TOC format where:
        - Title is on one line
        - Page number is on the next line (standalone)

        Example:
            الفصل الأول: المقدمة
            ١٥

            الفصل الثاني: النظرية
            ٣٢

        Also handles:
        - Arabic-Indic digits (٠-٩)
        - Western digits (0-9)
        - Page number ranges (e.g., "15-20" -> take first number)

        Returns:
            List of dicts with 'title' and 'page' keys
        """
        lines = toc_text.split('\n')
        entries = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Skip obvious headers/footers
            if len(line) < 3 or self._is_header_footer(line):
                i += 1
                continue

            # Check if next line is a page number
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                # Normalize Arabic-Indic digits (٠-٩) to Western (0-9)
                next_line_normalized = self._normalize_arabic_digits(next_line)

                # Check if next line is a page number (digits only or digit-digit range)
                page_match = re.match(r'^(\d+)(?:-\d+)?$', next_line_normalized)

                if page_match:
                    # This looks like a title-page pair
                    title = line
                    page_num = int(page_match.group(1))  # Use first number in range

                    # Sanity check: page number should be reasonable (1-9999)
                    if 1 <= page_num <= 9999:
                        entries.append({
                            "title": title,
                            "page": page_num
                        })

                        # Skip the page number line
                        i += 2
                        continue

            # If no format matched, move to next line
            i += 1

        logger.info(f"✅ Parsed {len(entries)} valid TOC entries")
        return entries

    def _create_sections(self, entries: List[dict], page_offset: int = 0) -> List[SectionInfo]:
        """
        Convert parsed entries into SectionInfo objects with page ranges.

        Each section's end page is calculated as (next section's start page - 1).
        For the last section, we set a placeholder (start + 100) which will be
        corrected by the caller based on the actual PDF page count.

        Args:
            entries: List of dicts with 'title' and 'page' keys (book page numbers)
            page_offset: Offset to add to book page numbers to get PDF page numbers (default: 0)

        Returns:
            List of SectionInfo objects with hierarchical IDs and page ranges (PDF page numbers)
        """
        sections = []

        for idx, entry in enumerate(entries):
            # Apply offset: book page -> PDF page
            page_start = entry["page"] + page_offset

            # Calculate page_end: until next section starts
            if idx + 1 < len(entries):
                page_end = (entries[idx + 1]["page"] + page_offset) - 1
            else:
                # Last section: set placeholder that caller will fix
                page_end = page_start + 100

            # Ensure page_end is never less than page_start
            page_end = max(page_start, page_end)

            sections.append(
                SectionInfo(
                    section_id=f"{idx + 1}",
                    title=entry["title"],
                    level=1,
                    page_start=page_start,
                    page_end=page_end
                )
            )

        return sections

    def _clean_entries(self, entries: List[dict]) -> List[dict]:
        """
        Clean and validate TOC entries.

        Removes entries that are likely contamination from body text:
        1. Page numbers that decrease (going backwards)
        2. Page numbers that jump too much (>500 pages)

        NOTE: Duplicate page numbers are ALLOWED since multiple sections
        can legitimately start on the same page (e.g., subsections).

        Args:
            entries: List of dicts with 'title' and 'page' keys

        Returns:
            Cleaned list of entries
        """
        if not entries:
            return []

        cleaned = []
        last_page = 0

        for entry in entries:
            page = entry["page"]

            # Skip if page goes backwards (but allow same page)
            if page < last_page:
                logger.debug(f"Skipping entry (page decreased): {entry['title']} -> {page}")
                continue

            # Skip if page jumps too much (likely body text contamination)
            if last_page > 0 and (page - last_page) > 500:
                logger.debug(f"Skipping entry (page jump too large): {entry['title']} -> {page}")
                continue

            # ALLOW duplicate page numbers (multiple sections can start on same page)
            cleaned.append(entry)
            last_page = page

        logger.info(
            f"Cleaned {len(entries)} entries -> {len(cleaned)} valid "
            f"(removed {len(entries) - len(cleaned)} invalid)"
        )

        return cleaned

    def _is_header_footer(self, line: str) -> bool:
        """
        Check if line is likely a header/footer.

        Common patterns:
        - Standalone page numbers (e.g., "15")
        - Common header words (e.g., "الفصل", "الباب")
        - Very short lines (<3 chars)
        """
        # Skip very short lines
        if len(line) < 3:
            return True

        # Normalize Arabic-Indic digits
        line_normalized = self._normalize_arabic_digits(line)

        # Skip standalone page numbers
        if re.match(r'^\d+$', line_normalized):
            return True

        # Skip common header patterns (but not TOC headers)
        if re.match(r'^(الفصل|الباب|Chapter|Part)\s*\d+$', line):
            return True

        return False

    def _write_eval_log(self, eval_data: dict):
        """Write evaluation log for Arabic TOC extraction to JSON file."""
        try:
            os.makedirs(EVAL_DIR, exist_ok=True)
            safe_title = re.sub(r'[^\w\s-]', '', eval_data.get('book_title', 'unknown'))[:50].strip().replace(' ', '_')
            filename = f"toc_eval_extract_{safe_title}.json"
            filepath = os.path.join(EVAL_DIR, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(eval_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Evaluation log written to {filepath}")
        except Exception as e:
            logger.warning(f"Failed to write evaluation log: {e}")

    def _fallback_section(self) -> SectionsReport:
        """
        Create a fallback section when TOC extraction fails.

        Returns a single section covering the entire book.
        The caller should fix the page_end based on actual PDF page count.
        """
        logger.warning("Creating fallback section (entire book)")

        fallback = SectionInfo(
            section_id="1",
            title="Full Book",
            level=1,
            page_start=1,
            page_end=9999  # Placeholder, caller will fix
        )

        return SectionsReport(
            bookmarks_found=False,
            sections=[fallback]
        )
