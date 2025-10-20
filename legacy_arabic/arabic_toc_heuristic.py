# app/services/arabic_toc_heuristic.py
"""
Arabic TOC heuristic extractor (fallback when bookmarks/TOC-page parsing fail).

What it does
------------
- Scans each page's *top area* for lines that look like Arabic headings.
- Uses text normalization + simple layout cues (top-of-page) to reduce noise.
- Ignores obvious non-headings (footnotes "(1)", URLs, mostly-Latin lines).
- Emits a SectionsReport with hierarchical section_ids.

When to use
----------
- Called by TocExtractor AFTER trying:
    1) native bookmarks
    2) TOC page parsing (toc_page_extractor)
- Works on *digital-text* pages. If pages are image-only, you'll need OCR (V5).

Tunable knobs
-------------
- TOP_FRACTION: portion of page height considered "top" (0.40 = top 40%)
- MIN_SECTIONS: minimum headings to accept before falling back to "Document"
- MAX_CANDIDATES_PER_PAGE: cap lines per page to avoid noise flood
"""

from __future__ import annotations
from typing import List, Tuple
import re
import fitz  # PyMuPDF
from ..models.schemas import SectionInfo, SectionsReport
from .arabic_normalizer import normalize_text

# ---------- Heuristic knobs ----------
TOP_FRACTION = 0.40             # scan top 40% of each page
MIN_SECTIONS = 2                # if fewer than this are found -> fallback
MAX_CANDIDATES_PER_PAGE = 25    # safety cap per page

# ---------- Heading patterns ----------
# Level-1 anchors (after normalization)
LEVEL1_PATTERNS = [
    r"^مقدمة\b",
    r"^تمهيد\b",
    r"^تعريف\b",
    r"^الخلاصة\b",
    r"^خلاصة\b",
    r"^الخاتمة\b",
    r"^الفهرس\b",
    r"^المراجع\b",
    r"^الشكر\b",
    r"^الملحق\b",
    r"^الفصل\s+(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|[0-9]+)\b",
    r"^الباب\s+(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|[0-9]+)\b",
    r"^الجزء\s+(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|[0-9]+)\b",
]
LEVEL1_RE = re.compile("|".join(LEVEL1_PATTERNS))

# Level-2+ patterns (numbers like 1.1 or 1-2, and cautious "(1) Title" form)
LEVELN_PATTERNS = [
    r"^[0-9]+\.[0-9]+\s+",       # 1.1  Title
    r"^[0-9]+[-–][0-9]+\s+",     # 1-1  Title
    r"^\(?[0-9]+\)?\s+[^\d]\S+", # (1)  Title   (very cautious)
]
LEVELN_RE = re.compile("|".join(LEVELN_PATTERNS))

# Obvious non-headings: footnotes, URLs, etc.
NEGATIVE_RE = re.compile(r"^\(\d+\)|https?://|www\.", re.IGNORECASE)

def _arabic_heavy(raw: str) -> bool:
    """Reject lines that are mostly ASCII/Latin (citations/URLs)."""
    if not raw:
        return False
    ascii_letters = sum(ch.isascii() and ch.isalpha() for ch in raw)
    return ascii_letters <= max(3, int(len(raw) * 0.4))

def _level_for_line(text_norm: str) -> int | None:
    if LEVEL1_RE.search(text_norm):
        return 1
    if LEVELN_RE.search(text_norm):
        return 2
    return None


class ArabicTocHeuristic:
    """Heuristic section detector for Arabic PDFs (fallback)."""

    def extract(self, pdf_bytes: bytes) -> SectionsReport:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        num_pages = doc.page_count

        candidates: List[Tuple[int, str, int]] = []  # (level, title, page_start)

        for i, page in enumerate(doc, start=1):
            rect = page.rect
            top_cut = rect.y0 + rect.height * TOP_FRACTION

            # Prefer rich structure ("dict"); fallback to "blocks"
            used = False
            try:
                content = page.get_text("dict")["blocks"]  # list of blocks
                lines_seen = 0
                for block in content:
                    for line in block.get("lines", []):
                        if lines_seen >= MAX_CANDIDATES_PER_PAGE:
                            break
                        # smallest Y among spans in this line
                        y0 = min((s["bbox"][1] for s in line.get("spans", []) if "bbox" in s), default=None)
                        if y0 is None or y0 > top_cut:
                            continue
                        raw = " ".join(s.get("text", "") for s in line.get("spans", []))
                        raw = raw.strip()
                        if not raw:
                            continue
                        if NEGATIVE_RE.search(raw):
                            continue
                        if not _arabic_heavy(raw):
                            continue

                        text_norm = normalize_text(raw)
                        lvl = _level_for_line(text_norm)
                        if lvl:
                            # Store normalized title for consistency
                            candidates.append((lvl, text_norm, i))
                            lines_seen += 1
                used = True
            except Exception:
                used = False

            if not used:
                # Fallback: coarser blocks API
                blocks = page.get_text("blocks") or []
                kept = 0
                for x0, y0, x1, y1, raw, *_ in blocks:
                    if kept >= MAX_CANDIDATES_PER_PAGE:
                        break
                    if y0 > top_cut:
                        continue
                    raw = (raw or "").strip()
                    if not raw:
                        continue
                    if NEGATIVE_RE.search(raw):
                        continue
                    if not _arabic_heavy(raw):
                        continue

                    text_norm = normalize_text(raw)
                    lvl = _level_for_line(text_norm)
                    if lvl:
                        candidates.append((lvl, text_norm, i))
                        kept += 1

        # Small cleanups: dedupe consecutive identical titles on same page
        dedup: List[Tuple[int, str, int]] = []
        for c in candidates:
            if not dedup or c != dedup[-1]:
                dedup.append(c)
        candidates = dedup

        # If too few, bail out gracefully
        if len(candidates) < MIN_SECTIONS:
            only = SectionInfo(section_id="1", title="Document", level=1, page_start=1, page_end=num_pages)
            return SectionsReport(bookmarks_found=False, sections=[only])

        # Build sections based on next same-or-higher-level heading
        sections: List[SectionInfo] = []
        counters: List[int] = []  # hierarchical counters per level

        for idx, (lvl, title, pstart) in enumerate(candidates):
            # BOOTSTRAP: ensure first section starts at level 1 (avoid '0.x' IDs)
            if idx == 0 and lvl > 1:
                lvl = 1

            pend = num_pages
            for j in range(idx + 1, len(candidates)):
                lvl_j, _, p_j = candidates[j]
                if lvl_j <= lvl:
                    pend = max(pstart, p_j - 1)
                    break

            # Resize counters to current level, then increment current level
            if len(counters) < lvl:
                counters.extend([0] * (lvl - len(counters)))
            counters = counters[:lvl]
            counters[lvl - 1] += 1

            section_id = ".".join(str(n) for n in counters)
            sections.append(
                SectionInfo(
                    section_id=section_id,
                    title=title.strip() or f"Section {section_id}",
                    level=lvl,
                    page_start=pstart,
                    page_end=pend,
                )
            )

        return SectionsReport(bookmarks_found=False, sections=sections)
