# app/services/toc_page_extractor.py
"""
Arabic TOC page extractor.

- Scans early pages (prefers page 5) for a TOC page labeled with Arabic keywords
  or containing many lines that look like "page-number + title" or "title ... page-number".
- Builds a SectionsReport where each entry is level=1 with proper page ranges.
- Designed to be called BEFORE the heuristic fallback.

Usage:
    from .toc_page_extractor import TocPageExtractor
    report = TocPageExtractor().find_and_parse(pdf_bytes)
    if report: return report
"""


from __future__ import annotations
from typing import List, Optional, Tuple
import re
import fitz  # PyMuPDF
from fastapi import HTTPException
from .models.schemas import SectionInfo, SectionsReport
from .arabic_normalizer import normalize_text, has_arabic

# ---------- Config (tweak as needed) ----------
MAX_SCAN_PAGES = 12           # Not used when explicit indices provided (kept for clarity)
MIN_TOC_LINES = 3             # Minimal number of parseable TOC lines to accept a page as TOC

# Prefer the known TOC page index (0-based). For many books this is page 5 => index 4.
PREFERRED_TOC_PAGE_INDEX = 4

# If the preferred page fails, scan this early window (0-based inclusive range).
SCAN_START_INDEX = 2          # page 3
SCAN_END_INDEX = 9            # page 10

# Keywords that often label the TOC page (after normalization).
TOC_KEYWORDS = ("المحتويات", "فهرس المحتويات", "جدول المحتويات", "الفهرس")

# ---------- Regexes ----------
# Number-first lines (e.g., "9 تمهيد السلسلة")
RE_NUM_FIRST = re.compile(r"^\s*([0-9٠-٩۰-۹]{1,4})\s+(.{3,})$")
# Number-last lines (e.g., "تمهيد السلسلة … 9")
RE_NUM_LAST  = re.compile(r"^(.{3,}?)\s*[\.·\s…]*\s*([0-9٠-٩۰-۹]{1,4})\s*$")

# Negative filters: drop obvious non-headings (footnotes/URLs/citations)
NEGATIVE_RE = re.compile(r"^\(\d+\)|https?://|www\.", re.IGNORECASE)

def _looks_arabic_heavy(s: str) -> bool:
    """Reject lines that are mostly ASCII/Latin (citations/URLs)."""
    if not s:
        return False
    ascii_letters = sum(ch.isascii() and ch.isalpha() for ch in s)
    return ascii_letters <= max(3, int(len(s) * 0.4))

def _to_int(nstr: str) -> int:
    # Arabic-Indic and Eastern Arabic-Indic -> Western digits
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    return int(nstr.translate(trans))


class TocPageExtractor:
    """Extracts sections from an Arabic TOC page if present."""

    def _candidate_pages(self, num_pages: int) -> List[int]:
        """Build a list of page indices to check, preferring page 5 (index 4)."""
        indices: list[int] = []
        if PREFERRED_TOC_PAGE_INDEX is not None and PREFERRED_TOC_PAGE_INDEX < num_pages:
            indices.append(PREFERRED_TOC_PAGE_INDEX)
        start = max(0, SCAN_START_INDEX)
        end = min(SCAN_END_INDEX, num_pages - 1)
        indices.extend([i for i in range(start, end + 1) if i not in indices])
        return indices

    def find_and_parse(self, pdf_bytes: bytes) -> Optional[SectionsReport]:
        """Return a SectionsReport if a TOC page is detected; otherwise None."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupt PDF: {e}")

        num_pages = doc.page_count
        if num_pages <= 0:
            return None

        best: Tuple[int, List[Tuple[int, str]]] | None = None  # (page_idx, [(page_num, title)])

        for i in self._candidate_pages(num_pages):
            page = doc.load_page(i)
            raw_text = page.get_text("text") or ""
            if not raw_text:
                continue

            text_norm = normalize_text(raw_text)
            toc_lines: List[Tuple[int, str]] = []

            # Parse each normalized line for number+title pairs
            for line in text_norm.splitlines():
                line = line.strip()
                if len(line) < 3:
                    continue

                # number-first pattern
                m1 = RE_NUM_FIRST.match(line)
                if m1:
                    pnum = _to_int(m1.group(1))
                    title = m1.group(2).strip().strip(".·…")
                    # strip stray numbers at edges
                    title = re.sub(r"^[0-9]+\s+", "", title)
                    title = re.sub(r"\s+[0-9]+$", "", title)
                    # filters
                    if not (1 <= pnum <= num_pages):
                        continue
                    if NEGATIVE_RE.search(title):
                        continue
                    if not _looks_arabic_heavy(title):
                        continue
                    if has_arabic(title):
                        toc_lines.append((pnum, title))
                    continue

                # number-last pattern
                m2 = RE_NUM_LAST.match(line)
                if m2:
                    title = m2.group(1).strip().strip(".·…")
                    pnum = _to_int(m2.group(2))
                    # strip stray numbers at edges
                    title = re.sub(r"^[0-9]+\s+", "", title)
                    title = re.sub(r"\s+[0-9]+$", "", title)
                    # filters
                    if not (1 <= pnum <= num_pages):
                        continue
                    if NEGATIVE_RE.search(title):
                        continue
                    if not _looks_arabic_heavy(title):
                        continue
                    if has_arabic(title):
                        toc_lines.append((pnum, title))

            # Decide if this page is the TOC page
            if any(k in text_norm for k in TOC_KEYWORDS) or len(toc_lines) >= MIN_TOC_LINES:
                # Keep the densest TOC-like page
                if best is None or len(toc_lines) > len(best[1]):
                    best = (i, toc_lines)

        if not best:
            return None

        # Build sections from the best page's pairs
        _, lines = best
        if not lines:
            return None

        # Sort by page number and enforce strictly increasing pages
        lines = sorted(lines, key=lambda x: x[0])
        entries: List[Tuple[int, str, int]] = []
        last_p = 0
        for pnum, title in lines:
            if pnum <= last_p or pnum < 1 or pnum > num_pages:
                continue
            # Normalize title for consistent output
            title_norm = normalize_text(title)
            entries.append((1, title_norm, pnum))  # level=1 for simplicity/robustness
            last_p = pnum

        if len(entries) < 2:
            return None

        # Convert entries to contiguous sections
        sections: List[SectionInfo] = []
        for idx, (lvl, title, pstart) in enumerate(entries):
            pend = num_pages
            if idx + 1 < len(entries):
                pend = max(pstart, entries[idx + 1][2] - 1)
            section_id = str(idx + 1)  # 1-based sequential
            sections.append(
                SectionInfo(
                    section_id=section_id,
                    title=title,
                    level=lvl,
                    page_start=pstart,
                    page_end=pend,
                )
            )

        return SectionsReport(bookmarks_found=False, sections=sections)
