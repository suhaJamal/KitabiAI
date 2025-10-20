# app/services/export_service.py
"""
Exports analysis results to JSONL (canonical).
Each line = one page record with page, has_text, image_count, and optional text.
"""

import json
from typing import Iterable
from ..models.schemas import AnalysisReport, PageInfo

class ExportService:
    def to_jsonl(self, report: AnalysisReport, include_text: bool = True) -> bytes:
        """
        Convert an AnalysisReport to JSONL bytes.
        """
        def iter_rows(pages: Iterable[PageInfo]):
            for p in pages:
                row = {
                    "page": p.page,
                    "has_text": p.has_text,
                    "image_count": p.image_count,
                }
                if include_text:
                    row["text"] = p.text or ""
                yield row

        lines = (json.dumps(row, ensure_ascii=False) for row in iter_rows(report.pages))
        data = "\n".join(lines) + "\n"
        return data.encode("utf-8")
