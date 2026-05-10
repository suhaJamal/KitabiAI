# app/services/toc_generator.py
"""
TOC Generator - Generate Table of Contents from detected headings.

This module provides an alternative to TOC extraction by detecting section
headings (titles) throughout the document using Azure Document Intelligence's
paragraph role detection.

Advantages over extraction:
1. Works for books without formal TOC pages
2. No page offset problem (uses actual PDF page numbers)
3. More robust for old/scanned books
4. Generates accurate section boundaries

Author: Suha Islaih
Date: January 2026
"""

import logging
import json
import os
import re
from datetime import datetime
from typing import List, Optional, Any, Dict, Tuple

from ...models.schemas import SectionInfo, SectionsReport


logger = logging.getLogger(__name__)

# Evaluation log directory
EVAL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'evaluation')

# Minimum font size to consider as heading (in points)
MIN_HEADING_FONT_SIZE = 16.0

class TocGenerator:
    """
    Generate Table of Contents by detecting headings throughout the document.

    Uses Azure Document Intelligence's paragraph role detection to identify:
    - "title" - Main titles (level 1)
    - "sectionHeading" - Section headings (level 2+)

    The generator processes all pages and builds a TOC from detected headings,
    storing the actual content for each section to avoid overlap issues.
    """

    # Minimum heading length to be considered valid
    MIN_HEADING_LENGTH = 3

    # Maximum heading length (longer text is likely body content, not a heading)
    MAX_HEADING_LENGTH = 200

    # Roles that indicate a heading (from Azure Document Intelligence)
    HEADING_ROLES = ["title", "sectionHeading"]

    def __init__(self):
        """Initialize the TOC generator."""
        pass

    def generate(
        self,
        azure_result: Any,
        num_pages: int,
        store_content: bool = True,
        book_title: str = "unknown",
        content_start_page: int = 1
    ) -> SectionsReport:
        """
        Generate TOC from Azure Document Intelligence result.

        Scans all pages for paragraphs with heading roles and builds
        a hierarchical TOC structure.

        Args:
            azure_result: Full Azure Document Intelligence result object
            num_pages: Total number of pages in the PDF
            store_content: If True, store section content directly (recommended)
                          If False, only store page ranges
            book_title: Book title for evaluation logging

        Returns:
            SectionsReport containing generated sections with accurate page numbers
        """
        logger.info("Starting TOC generation from headings")

        if not azure_result:
            logger.warning("No Azure result provided. Returning fallback section.")
            return self._fallback_section(num_pages)

        # Check if paragraphs exist in Azure result
        if not hasattr(azure_result, 'paragraphs') or not azure_result.paragraphs:
            logger.warning("No paragraphs in Azure result. Returning fallback section.")
            return self._fallback_section(num_pages)

        # Step 1: Extract all headings with their positions (with eval tracking)
        self._eval_candidates = []
        self._eval_filtered = []
        headings = self._extract_headings(azure_result, content_start_page)

        if not headings:
            logger.warning("No headings found in document. Returning fallback section.")
            self._write_eval_log(book_title, num_pages, headings=[], sections=[])
            return self._fallback_section(num_pages)

        logger.info(f"Found {len(headings)} headings in document")

        # Step 2: Build page paragraphs map for Y-position-based content extraction
        page_paragraphs_map = {}
        if store_content:
            page_paragraphs_map = self._build_page_paragraphs_map(azure_result)

        # Step 3: Create sections from headings
        sections = self._create_sections_from_headings(
            headings,
            num_pages,
            page_paragraphs_map if store_content else None
        )

        if not sections:
            logger.warning("Failed to create sections from headings. Returning fallback.")
            self._write_eval_log(book_title, num_pages, headings=headings, sections=[])
            return self._fallback_section(num_pages)

        logger.info(f"Generated TOC with {len(sections)} sections")

        # Write evaluation log
        self._write_eval_log(book_title, num_pages, headings=headings, sections=sections)

        return SectionsReport(
            bookmarks_found=True,  # Using same field to indicate TOC was found/generated
            sections=sections
        )

    def _extract_headings(self, azure_result: Any, content_start_page: int = 1) -> List[Dict]:
        """
        Extract all headings from Azure result.

        Looks for paragraphs with role = "title" or "sectionHeading".

        Args:
            azure_result: Azure Document Intelligence result

        Returns:
            List of heading dictionaries with:
            - title: Heading text
            - page: PDF page number (1-based)
            - role: "title" or "sectionHeading"
            - offset: Character offset within the page (for precise content splitting)
            - length: Length of the heading text
        """
        headings = []

        for paragraph in azure_result.paragraphs:
            # Check if this paragraph has a heading role
            role = getattr(paragraph, 'role', None)
            if role not in self.HEADING_ROLES:
                continue

            # Get heading content
            content = getattr(paragraph, 'content', '').strip()

            # Get page number from bounding regions (needed for eval logging)
            page_number = None
            if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
                page_number = paragraph.bounding_regions[0].page_number

            # Get bounding box height and Y position
            height = None
            y_top = None
            y_bottom = None
            if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
                region = paragraph.bounding_regions[0]
                if hasattr(region, 'polygon') and region.polygon:
                    y_coords = [region.polygon[i] for i in range(1, len(region.polygon), 2)]
                    y_top = min(y_coords)
                    y_bottom = max(y_coords)
                    height = y_bottom - y_top

            # Record this candidate for evaluation BEFORE any filtering
            candidate = {
                'content': content,
                'page': page_number,
                'role': role,
                'height': round(height, 4) if height else None
            }
            self._eval_candidates.append(candidate)

            # --- FILTERS START ---

            # Filter 1: Skip if content is purely numeric (page numbers)
            if re.match(r'^[\d\u0660-\u0669\s\.\-]+$', content):
                self._eval_filtered.append({**candidate, 'reason': 'numeric_content'})
                continue

            # Filter 2: Check bounding box height (filter small inline headings)
            MIN_HEIGHT = 0.025  # Minimum height ratio - adjust as needed (0.02-0.03)
            if height is not None and height < MIN_HEIGHT:
                self._eval_filtered.append({**candidate, 'reason': f'height_too_small ({height:.4f} < {MIN_HEIGHT})'})
                logger.debug(f"Skipping small heading (height {height:.4f}): {content[:30]}")
                continue

            # Filter 3: Check font size from paragraph styles/spans
            font_size = None
            if hasattr(paragraph, 'spans') and paragraph.spans:
                span = paragraph.spans[0]
                if hasattr(span, 'font') and hasattr(span.font, 'size'):
                    font_size = span.font.size

            # Skip if font size is too small (and we have font info)
            if font_size is not None and font_size < self.MIN_HEADING_FONT_SIZE:
                self._eval_filtered.append({**candidate, 'reason': f'font_too_small ({font_size})'})
                continue

            # Filter 4: Validate heading length
            if len(content) < self.MIN_HEADING_LENGTH:
                self._eval_filtered.append({**candidate, 'reason': f'too_short ({len(content)} chars)'})
                continue
            if len(content) > self.MAX_HEADING_LENGTH:
                self._eval_filtered.append({**candidate, 'reason': f'too_long ({len(content)} chars)'})
                logger.debug(f"Skipping too-long heading: {content[:50]}...")
                continue

            # Filter 5: No page number
            if page_number is None:
                self._eval_filtered.append({**candidate, 'reason': 'no_page_number'})
                logger.debug(f"Skipping heading without page number: {content[:50]}...")
                continue

            # --- FILTERS END --- Heading accepted

            # Get character offset from spans (for precise content splitting)
            offset = None
            length = None
            if hasattr(paragraph, 'spans') and paragraph.spans:
                offset = paragraph.spans[0].offset
                length = paragraph.spans[0].length

            heading = {
                'title': content,
                'page': page_number,
                'role': role,
                'offset': offset,
                'length': length,
                'y_top': y_top,
                'y_bottom': y_bottom,
            }

            headings.append(heading)
            logger.debug(f"Found heading: '{content[:50]}...' on page {page_number} (role: {role})")

        # Sort by page number, then by offset within page
        headings.sort(key=lambda h: (h['page'], h['offset'] or 0))

        # Skip pre-content pages (cover, license, table of contents, etc.)
        if content_start_page > 1:
            before = len(headings)
            headings = [h for h in headings if h['page'] >= content_start_page]
            logger.info(f"Skipped {before - len(headings)} headings before page {content_start_page}")

        # Merge consecutive heading paragraphs on the same page that are close
        # together vertically — these are two-line section titles split across spans
        if len(headings) > 1:
            merged: List[Dict] = []
            skip = False
            for idx in range(len(headings)):
                if skip:
                    skip = False
                    continue
                h = headings[idx]
                if idx + 1 < len(headings):
                    nxt = headings[idx + 1]
                    same_page = nxt['page'] == h['page']
                    close_y = (
                        h.get('y_bottom') is not None
                        and nxt.get('y_top') is not None
                        and (nxt['y_top'] - h['y_bottom']) < 0.5
                    )
                    if same_page and close_y:
                        combined = dict(h)
                        combined['title'] = h['title'] + " " + nxt['title']
                        combined['y_bottom'] = nxt['y_bottom']
                        merged.append(combined)
                        skip = True
                        logger.debug(f"Merged two-line heading: '{combined['title'][:60]}' on page {h['page']}")
                        continue
                merged.append(h)
            headings = merged

        return headings

    # Paragraph roles that represent structural/layout elements, not body content
    _SKIP_ROLES = {'pageHeader', 'pageFooter', 'pageNumber', 'footnote'}

    # Margin in inches — paragraphs within this distance from page top/bottom are skipped
    _MARGIN_INCHES = 0.4

    def _build_page_paragraphs_map(self, azure_result: Any) -> Dict[int, List[Dict]]:
        """
        Build a map of page number to list of paragraphs with Y-positions.

        Each paragraph entry: {'content': str, 'y_top': float, 'y_bottom': float}
        Y values are in inches from the top of the page.

        Excludes headers, footers, page numbers, and footnotes (by role and Y-position).

        Args:
            azure_result: Azure Document Intelligence result

        Returns:
            Dictionary mapping page number to ordered list of paragraph dicts
        """
        page_paragraphs: Dict[int, List[Dict]] = {}

        if not hasattr(azure_result, 'paragraphs') or not azure_result.paragraphs:
            return page_paragraphs

        # Build page height map to enable Y-position margin filtering
        page_heights: Dict[int, float] = {}
        if hasattr(azure_result, 'pages') and azure_result.pages:
            for page in azure_result.pages:
                if hasattr(page, 'page_number') and hasattr(page, 'height') and page.height:
                    page_heights[page.page_number] = page.height

        for paragraph in azure_result.paragraphs:
            # Skip header/footer/page-number/footnote roles
            role = getattr(paragraph, 'role', None)
            if role in self._SKIP_ROLES:
                continue

            content = getattr(paragraph, 'content', '').strip()
            if not content:
                continue

            if not (hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions):
                continue

            region = paragraph.bounding_regions[0]
            page_num = region.page_number

            y_top = None
            y_bottom = None
            if hasattr(region, 'polygon') and region.polygon:
                y_coords = [region.polygon[i] for i in range(1, len(region.polygon), 2)]
                y_top = min(y_coords)
                y_bottom = max(y_coords)

            # Skip paragraphs inside top/bottom margin (catches unlabelled headers/footers)
            page_height = page_heights.get(page_num)
            if page_height and y_top is not None and y_bottom is not None:
                if y_top < self._MARGIN_INCHES or y_bottom > (page_height - self._MARGIN_INCHES):
                    continue

            if page_num not in page_paragraphs:
                page_paragraphs[page_num] = []

            page_paragraphs[page_num].append({
                'content': content,
                'y_top': y_top,
                'y_bottom': y_bottom,
            })

        # Sort each page's paragraphs by Y position (top to bottom)
        for page_num in page_paragraphs:
            page_paragraphs[page_num].sort(key=lambda p: p['y_top'] or 0)

        logger.debug(f"Built paragraph map for {len(page_paragraphs)} pages")
        return page_paragraphs

    def fill_content_from_azure(
        self,
        sections: List[SectionInfo],
        azure_result: Any
    ) -> List[SectionInfo]:
        """
        Fill section.content for sections that don't already have it, using
        Azure paragraph Y-positions to slice content at heading boundaries.

        Used by the extract TOC path where sections have page ranges but no
        content — the same Y-position logic used by the generate path is
        applied by finding each heading's Y-position via title text matching.

        Args:
            sections: List of SectionInfo objects (page_start/page_end already set)
            azure_result: Full Azure Document Intelligence result object

        Returns:
            The same list with section.content filled in where possible
        """
        if not azure_result:
            return sections

        page_paragraphs_map = self._build_page_paragraphs_map(azure_result)
        if not page_paragraphs_map:
            return sections

        for idx, section in enumerate(sections):
            if section.content is not None:
                continue  # Already has content from generate path

            next_section = sections[idx + 1] if idx + 1 < len(sections) else None

            heading_y_bottom = self._find_heading_y(
                section.title, section.page_start, page_paragraphs_map
            )

            next_heading = None
            if next_section:
                next_heading_y_top = self._find_heading_y_top(
                    next_section.title, next_section.page_start, page_paragraphs_map
                )
                if next_heading_y_top is not None:
                    next_heading = {
                        'page': next_section.page_start,
                        'y_top': next_heading_y_top,
                    }

            heading = {
                'page': section.page_start,
                'y_bottom': heading_y_bottom,
            }

            content = self._extract_section_content_by_y(
                heading, next_heading, page_paragraphs_map, section.page_end
            )
            if content:
                section.content = content

        logger.info(f"Filled content for {len(sections)} sections using Azure Y-positions")
        return sections

    def _find_heading_y(
        self,
        title: str,
        page_num: int,
        page_paragraphs_map: Dict[int, List[Dict]]
    ) -> Optional[float]:
        """
        Find the y_bottom of a heading paragraph by matching title text on a page.
        Returns None if not found (caller will include the full page as fallback).
        """
        paragraphs = page_paragraphs_map.get(page_num, [])
        title_normalized = title.strip()
        for para in paragraphs:
            para_content = para['content'].strip()
            if title_normalized in para_content or para_content in title_normalized:
                return para.get('y_bottom')
        return None

    def _find_heading_y_top(
        self,
        title: str,
        page_num: int,
        page_paragraphs_map: Dict[int, List[Dict]]
    ) -> Optional[float]:
        """
        Find the y_top of a heading paragraph by matching title text on a page.
        Returns None if not found (caller will include the full page as fallback).
        """
        paragraphs = page_paragraphs_map.get(page_num, [])
        title_normalized = title.strip()
        for para in paragraphs:
            para_content = para['content'].strip()
            if title_normalized in para_content or para_content in title_normalized:
                return para.get('y_top')
        return None

    def _create_sections_from_headings(
        self,
        headings: List[Dict],
        num_pages: int,
        page_paragraphs_map: Optional[Dict[int, List[Dict]]] = None
    ) -> List[SectionInfo]:
        """
        Create SectionInfo objects from extracted headings.

        Calculates page ranges and extracts content using Y-position filtering
        so that only text below the heading on the first page is included.

        Args:
            headings: List of heading dictionaries (must include y_top, y_bottom)
            num_pages: Total number of pages
            page_paragraphs_map: Optional per-page paragraph list with Y positions

        Returns:
            List of SectionInfo objects
        """
        sections = []

        for idx, heading in enumerate(headings):
            # Calculate page range
            page_start = heading['page']

            # Page end is (next heading's page - 1) or last page
            if idx + 1 < len(headings):
                next_heading = headings[idx + 1]
                # If next heading is on same page, this section is just that page
                if next_heading['page'] == page_start:
                    page_end = page_start
                else:
                    page_end = next_heading['page'] - 1
            else:
                # Last section extends to end of document
                page_end = num_pages

            # Ensure page_end is not less than page_start
            page_end = max(page_start, page_end)

            # Determine level based on role
            level = 1 if heading['role'] == 'title' else 2

            # Extract content using Y-position filtering if paragraphs map is available
            content = None
            if page_paragraphs_map:
                next_h = headings[idx + 1] if idx + 1 < len(headings) else None
                content = self._extract_section_content_by_y(
                    heading, next_h, page_paragraphs_map, page_end
                )

            # Create section
            section = SectionInfo(
                section_id=str(idx + 1),
                title=heading['title'],
                level=level,
                page_start=page_start,
                page_end=page_end,
                content=content
            )

            sections.append(section)

            logger.debug(
                f"Created section: '{heading['title'][:30]}' "
                f"(pages {page_start}-{page_end}, level {level}, "
                f"content={'yes' if content else 'no'})"
            )

        return sections

    def _extract_section_content_by_y(
        self,
        heading: Dict,
        next_heading: Optional[Dict],
        page_paragraphs_map: Dict[int, List[Dict]],
        page_end: int
    ) -> str:
        """
        Extract content for a section using Y-position filtering.

        - First page (page_start): only paragraphs whose y_top >= heading's y_bottom
          (skips everything above and including the heading title itself).
        - Middle pages: all paragraphs included.
        - Boundary page (where next heading starts): only paragraphs whose
          y_top < next heading's y_top — this captures content that sits above
          the next heading on that shared page, which belongs to the current section.
          This fixes two symptoms:
            1. Previous section was missing its tail content above the next heading.
            2. Current section was cut off before its actual end on the boundary page.

        Args:
            heading: Current heading dict (must include 'page', 'y_bottom')
            next_heading: Next heading dict or None if last section
            page_paragraphs_map: Per-page list of {'content', 'y_top', 'y_bottom'}
            page_end: page_end stored in SectionInfo (used only when there is no next heading)

        Returns:
            Section content text
        """
        page_start = heading['page']
        heading_y_bottom = heading.get('y_bottom')

        # Determine the last page to process and its Y cutoff
        if next_heading is None:
            # Last section in document — include all remaining pages
            last_page = page_end
            last_page_y_cutoff = None
        elif next_heading['page'] == page_start:
            # Both headings on the same page — one-page section
            last_page = page_start
            last_page_y_cutoff = next_heading.get('y_top')
        else:
            # Extend into next heading's page to capture content above that heading
            last_page = next_heading['page']
            last_page_y_cutoff = next_heading.get('y_top')

        content_parts = []

        for page_num in range(page_start, last_page + 1):
            paragraphs = page_paragraphs_map.get(page_num, [])
            if not paragraphs:
                continue

            selected = []
            for para in paragraphs:
                y_top = para.get('y_top')

                # First page: skip paragraphs at or above the heading's bottom edge
                if page_num == page_start and heading_y_bottom is not None and y_top is not None:
                    if y_top < heading_y_bottom:
                        continue

                # Boundary page: stop before the next heading
                if page_num == last_page and last_page_y_cutoff is not None and y_top is not None:
                    if y_top >= last_page_y_cutoff:
                        continue

                selected.append(para['content'])

            if selected:
                content_parts.append("\n".join(selected))

        return "\n\n".join(content_parts)

    def _write_eval_log(self, book_title: str, num_pages: int, headings: list, sections: list):
        """Write evaluation log for TOC generation to JSON file."""
        try:
            os.makedirs(EVAL_DIR, exist_ok=True)

            # Count filter reasons
            filter_reasons = {}
            for item in self._eval_filtered:
                reason = item['reason'].split(' (')[0]  # Group by reason type
                filter_reasons[reason] = filter_reasons.get(reason, 0) + 1

            eval_data = {
                'book_title': book_title,
                'method': 'generate',
                'timestamp': datetime.now().isoformat(),
                'total_pages': num_pages,
                'candidates_before_filter': len(self._eval_candidates),
                'candidates_after_filter': len(headings),
                'sections_created': len(sections),
                'filter_summary': filter_reasons,
                'all_candidates': self._eval_candidates,
                'filtered_out': self._eval_filtered,
                'accepted_headings': [
                    {'title': h['title'], 'page': h['page'], 'role': h['role']}
                    for h in headings
                ],
                'final_sections': [
                    {
                        'title': s.title,
                        'page_start': s.page_start,
                        'page_end': s.page_end,
                        'level': s.level
                    }
                    for s in sections
                ]
            }

            safe_title = re.sub(r'[^\w\s-]', '', book_title)[:50].strip().replace(' ', '_')
            filename = f"toc_eval_generate_{safe_title}.json"
            filepath = os.path.join(EVAL_DIR, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(eval_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Evaluation log written to {filepath}")
        except Exception as e:
            logger.warning(f"Failed to write evaluation log: {e}")

    def _fallback_section(self, num_pages: int) -> SectionsReport:
        """
        Create a fallback section when TOC generation fails.

        Returns a single section covering the entire book.

        Args:
            num_pages: Total number of pages

        Returns:
            SectionsReport with single "Full Book" section
        """
        logger.warning("Creating fallback section (entire book)")

        fallback = SectionInfo(
            section_id="1",
            title="Full Book",
            level=1,
            page_start=1,
            page_end=num_pages
        )

        return SectionsReport(
            bookmarks_found=False,
            sections=[fallback]
        )
