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
from typing import List, Optional, Any, Dict, Tuple

from ..models.schemas import SectionInfo, SectionsReport


logger = logging.getLogger(__name__)
import re

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
        store_content: bool = True
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

        # Step 1: Extract all headings with their positions
        headings = self._extract_headings(azure_result)

        if not headings:
            logger.warning("No headings found in document. Returning fallback section.")
            return self._fallback_section(num_pages)

        logger.info(f"Found {len(headings)} headings in document")

        # Step 2: Build page content map for content extraction
        page_content_map = {}
        if store_content:
            page_content_map = self._build_page_content_map(azure_result)

        # Step 3: Create sections from headings
        sections = self._create_sections_from_headings(
            headings,
            num_pages,
            page_content_map if store_content else None
        )

        if not sections:
            logger.warning("Failed to create sections from headings. Returning fallback.")
            return self._fallback_section(num_pages)

        logger.info(f"Generated TOC with {len(sections)} sections")

        return SectionsReport(
            bookmarks_found=True,  # Using same field to indicate TOC was found/generated
            sections=sections
        )

    def _extract_headings(self, azure_result: Any) -> List[Dict]:
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
            # Skip if content is purely numeric (page numbers)
            
            if re.match(r'^[\d\u0660-\u0669\s\.\-]+$', content):
                continue
            # Check bounding box height (filter small inline headings)
            MIN_HEIGHT = 0.025  # Minimum height ratio - adjust as needed (0.02-0.03)

            if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
                region = paragraph.bounding_regions[0]
                if hasattr(region, 'polygon') and region.polygon:
                    # polygon is list of points [x1,y1, x2,y2, x3,y3, x4,y4]
                    y_coords = [region.polygon[i] for i in range(1, len(region.polygon), 2)]
                    height = max(y_coords) - min(y_coords)
                    
                    #logger.info(f"Heading: '{content[:40]}' | height: {height:.4f}")

                    if height < MIN_HEIGHT:
                        logger.debug(f"Skipping small heading (height {height:.4f}): {content[:30]}")
                        continue

            # Check font size from paragraph styles/spans
            font_size = None
            if hasattr(paragraph, 'spans') and paragraph.spans:
                span = paragraph.spans[0]
                if hasattr(span, 'font') and hasattr(span.font, 'size'):
                    font_size = span.font.size

            # Skip if font size is too small (and we have font info)
            if font_size is not None and font_size < self.MIN_HEADING_FONT_SIZE:
                continue

            # Validate heading length
            if len(content) < self.MIN_HEADING_LENGTH:
                continue
            if len(content) > self.MAX_HEADING_LENGTH:
                logger.debug(f"Skipping too-long heading: {content[:50]}...")
                continue

            # Get page number from bounding regions
            page_number = None
            if hasattr(paragraph, 'bounding_regions') and paragraph.bounding_regions:
                page_number = paragraph.bounding_regions[0].page_number

            if page_number is None:
                logger.debug(f"Skipping heading without page number: {content[:50]}...")
                continue

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
                'length': length
            }

            headings.append(heading)
            logger.debug(f"Found heading: '{content[:50]}...' on page {page_number} (role: {role})")

        # Sort by page number, then by offset within page
        headings.sort(key=lambda h: (h['page'], h['offset'] or 0))

        return headings

    def _build_page_content_map(self, azure_result: Any) -> Dict[int, str]:
        """
        Build a map of page number to page content.

        This is used for extracting section content.

        Args:
            azure_result: Azure Document Intelligence result

        Returns:
            Dictionary mapping page number to full page text
        """
        page_content = {}

        for page in azure_result.pages:
            page_num = page.page_number
            page_text = ""

            # Extract text from lines
            if hasattr(page, 'lines') and page.lines:
                for line in page.lines:
                    page_text += line.content + "\n"

            page_content[page_num] = page_text

        logger.debug(f"Built content map for {len(page_content)} pages")
        return page_content

    def _create_sections_from_headings(
        self,
        headings: List[Dict],
        num_pages: int,
        page_content_map: Optional[Dict[int, str]] = None
    ) -> List[SectionInfo]:
        """
        Create SectionInfo objects from extracted headings.

        Calculates page ranges and optionally extracts content for each section.

        Args:
            headings: List of heading dictionaries
            num_pages: Total number of pages
            page_content_map: Optional map of page number to content (for content extraction)

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

            # Create section
            section = SectionInfo(
                section_id=str(idx + 1),
                title=heading['title'],
                level=level,
                page_start=page_start,
                page_end=page_end
            )

            sections.append(section)

            logger.debug(
                f"Created section: '{heading['title'][:30]}...' "
                f"(pages {page_start}-{page_end}, level {level})"
            )

        return sections

    def _extract_section_content(
        self,
        headings: List[Dict],
        idx: int,
        page_content_map: Dict[int, str]
    ) -> str:
        """
        Extract content for a specific section.

        Uses character offsets to precisely split content at heading boundaries,
        avoiding overlap between sections.

        Args:
            headings: List of all headings
            idx: Index of current heading
            page_content_map: Map of page number to page content

        Returns:
            Section content text
        """
        heading = headings[idx]
        page_start = heading['page']

        # Determine where this section ends
        if idx + 1 < len(headings):
            next_heading = headings[idx + 1]
            page_end = next_heading['page']
            end_offset = next_heading['offset']
        else:
            page_end = max(page_content_map.keys()) if page_content_map else page_start
            end_offset = None

        content_parts = []

        for page_num in range(page_start, page_end + 1):
            page_text = page_content_map.get(page_num, "")

            if not page_text:
                continue

            # Handle first page of section
            if page_num == page_start:
                # Start after the heading
                start_offset = (heading['offset'] or 0) + (heading['length'] or 0)
                if page_num == page_end and end_offset is not None:
                    # Section starts and ends on same page
                    page_text = page_text[start_offset:end_offset]
                else:
                    # Section starts here but continues to next page
                    page_text = page_text[start_offset:]

            # Handle last page of section (if different from first)
            elif page_num == page_end and end_offset is not None:
                page_text = page_text[:end_offset]

            # Middle pages get full content (no slicing needed)

            content_parts.append(page_text.strip())

        return "\n\n".join(content_parts)

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
