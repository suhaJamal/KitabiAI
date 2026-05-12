# app/services/summarization/summarizer.py
"""
LLM-based summarization for book sections and full books.

Uses DeepSeek (OpenAI-compatible API) to generate:
- Per-section summaries (2-3 sentences)
- Full-book summary built hierarchically from section summaries

Language support: Arabic ('ar') and English ('en').
Model and credentials configured via settings (DEEPSEEK_API_KEY, etc.).
"""

import logging
import re
from datetime import datetime
from typing import Optional
import httpx

from ...core.config import settings
from ...models.database import SessionLocal, Book, Section, Category, Page

logger = logging.getLogger(__name__)

# Max content chars sent per section — keeps cost low while covering main ideas
_MAX_SECTION_CHARS = 3000

# Min content length to attempt summarization (very short sections are skipped)
_MIN_CONTENT_CHARS = 100

# Max section summaries fed into the book-level prompt
_MAX_SECTIONS_FOR_BOOK_SUMMARY = 60

_SECTION_PROMPTS = {
    'ar': (
        "لخّص القسم التالي وفق الهيكل الآتي:\n\n"
        "١. وصف عام (جملة أو جملتان): ما الذي يتناوله هذا القسم؟\n"
        "٢. أبرز المعلومات: اذكر الأشخاص الرئيسيين والأحداث والحقائق والتواريخ المهمة.\n\n"
        "أجب باللغة العربية فقط.\n\n"
        "عنوان القسم: {title}\n"
        "المحتوى:\n{content}\n\n"
        "الملخص:"
    ),
    'en': (
        "Summarize the following section using this structure:\n\n"
        "1. Overview (1-2 sentences): What does this section cover?\n"
        "2. Key highlights: List the main people, events, facts, and important dates.\n\n"
        "Reply in English only.\n\n"
        "Section title: {title}\n"
        "Content:\n{content}\n\n"
        "Summary:"
    ),
}

# Curated category list — LLM must pick exactly one from this list
PREDEFINED_CATEGORIES = [
    'فلسفة',
    'تاريخ',
    'أدب',
    'لغة عربية',
    'علوم دينية',
    'سياسة',
    'اقتصاد',
    'علم الاجتماع',
    'علم النفس',
    'تربية وتعليم',
    'فكر معاصر',
    'سيرة وتراجم',
    'علوم وتكنولوجيا',
    'فنون',
]

_CATEGORY_PROMPTS = {
    'ar': (
        "اختر تصنيفاً واحداً مناسباً من القائمة الآتية بناءً على ملخص الكتاب. "
        "أجب بالتصنيف فقط بدون أي كلمات إضافية.\n\n"
        "التصنيفات المتاحة:\n{categories}\n\n"
        "ملخص الكتاب: {summary}\n\n"
        "التصنيف:"
    ),
    'en': (
        "Choose exactly one category from the list below that best fits this book summary. "
        "Reply with the category name only, no extra words.\n\n"
        "Available categories:\n{categories}\n\n"
        "Book summary: {summary}\n\n"
        "Category:"
    ),
}

_KEYWORDS_PROMPTS = {
    'ar': (
        "بناءً على ملخص الكتاب التالي، اقترح من خمس إلى ثماني كلمات مفتاحية "
        "مفصولة بفواصل، باللغة العربية فقط، بدون ترقيم أو عناوين.\n\n"
        "ملخص الكتاب: {summary}\n\n"
        "الكلمات المفتاحية:"
    ),
    'en': (
        "Based on the following book summary, suggest 5 to 8 keywords separated by commas. "
        "Reply with keywords only, no numbering or headers.\n\n"
        "Book summary: {summary}\n\n"
        "Keywords:"
    ),
}

_BOOK_PROMPTS = {
    'ar': (
        "استناداً إلى ملخصات أقسام كتاب \"{title}\"، "
        "اكتب ملخصاً شاملاً للكتاب في أربع إلى ست جمل باللغة العربية.\n\n"
        "{section_summaries}\n\n"
        "ملخص الكتاب:"
    ),
    'en': (
        "Based on the following section summaries from the book \"{title}\", "
        "write a comprehensive book summary in 4-6 sentences.\n\n"
        "{section_summaries}\n\n"
        "Book summary:"
    ),
}


class Summarizer:
    """Generate LLM summaries for sections and books using DeepSeek."""

    def summarize_book(self, book_id: int) -> dict:
        """
        Summarize all sections of a book, then generate a book-level summary.

        Returns a result dict with counts of summarized/skipped sections.
        Raises ValueError if book not found, RuntimeError if API key missing.
        """
        if not settings.DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured in .env")

        db = SessionLocal()
        try:
            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                raise ValueError(f"Book {book_id} not found")

            language = book.language or 'ar'
            sections = (
                db.query(Section)
                .filter(Section.book_id == book_id)
                .order_by(Section.order_index)
                .all()
            )

            summarized = 0
            skipped = 0
            section_summaries = []

            for section in sections:
                # Prefer stored Y-position content; fall back to page-range text
                content = section.content
                if not content or len(content.strip()) < _MIN_CONTENT_CHARS:
                    content = self._get_content_from_pages(
                        book_id, section.page_start, section.page_end, db
                    )
                    if content:
                        logger.debug(
                            f"Section '{section.title}': using page-range fallback "
                            f"(pages {section.page_start}-{section.page_end})"
                        )

                if not content or len(content.strip()) < _MIN_CONTENT_CHARS:
                    skipped += 1
                    continue

                summary = self._summarize_section(section.title or "", content, language)
                if summary:
                    section.summary = summary
                    section_summaries.append(f"- {section.title}: {summary}")
                    summarized += 1
                    logger.debug(f"Summarized section '{section.title}' (book {book_id})")
                else:
                    skipped += 1

            db.flush()

            # Build book-level summary from section summaries
            book_summary_generated = False
            filled = {}
            if section_summaries:
                capped = section_summaries[:_MAX_SECTIONS_FOR_BOOK_SUMMARY]
                book_summary = self._summarize_book_from_sections(
                    book.title or "", capped, language
                )
                if book_summary:
                    book.summary = book_summary
                    book.summary_generated_at = datetime.utcnow()
                    book_summary_generated = True
                    # Auto-fill empty metadata fields from the book summary
                    filled = self._autofill_book_metadata(book, book_summary, language, db)

            db.commit()
            logger.info(
                f"Book {book_id} summarized: {summarized} sections, "
                f"{skipped} skipped, book summary={'yes' if book_summary_generated else 'no'}, "
                f"autofilled={filled}"
            )

            return {
                "ok": True,
                "sections_summarized": summarized,
                "sections_skipped": skipped,
                "book_summary_generated": book_summary_generated,
                **filled,
            }

        except (ValueError, RuntimeError):
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Summarization failed for book {book_id}: {e}")
            raise
        finally:
            db.close()

    def _summarize_section(self, title: str, content: str, language: str) -> Optional[str]:
        truncated = content[:_MAX_SECTION_CHARS]
        prompt_template = _SECTION_PROMPTS.get(language, _SECTION_PROMPTS['ar'])
        prompt = prompt_template.format(title=title, content=truncated)
        return self._call_llm(prompt)

    def _summarize_book_from_sections(
        self, title: str, section_summaries: list, language: str
    ) -> Optional[str]:
        summaries_text = "\n".join(section_summaries)
        prompt_template = _BOOK_PROMPTS.get(language, _BOOK_PROMPTS['ar'])
        prompt = prompt_template.format(title=title, section_summaries=summaries_text)
        return self._call_llm(prompt)

    def _get_content_from_pages(
        self, book_id: int, page_start: int, page_end: int, db
    ) -> Optional[str]:
        """
        Fallback: assemble section content from stored page texts when
        section.content is NULL (books uploaded before fill_content_from_azure).
        """
        pages = (
            db.query(Page)
            .filter(
                Page.book_id == book_id,
                Page.page_number >= page_start,
                Page.page_number <= page_end,
            )
            .order_by(Page.page_number)
            .all()
        )
        texts = [p.text for p in pages if p.text and p.text.strip()]
        return "\n\n".join(texts) if texts else None

    def _autofill_book_metadata(self, book, summary: str, language: str, db) -> dict:
        """
        Fill empty book metadata fields using the book summary.
        Never overwrites fields the admin already set.
        Returns a dict of what was filled for reporting.
        """
        filled = {}

        # 1. Description — use summary directly, no extra LLM call
        if not book.description:
            book.description = summary
            filled['description_set'] = True

        # 2. Category — pick one from predefined list
        if not book.category_id:
            predicted_name = self._predict_category(summary, language)
            if predicted_name:
                category = db.query(Category).filter(Category.name == predicted_name).first()
                if not category:
                    slug = re.sub(r'[\s_]+', '-', predicted_name.strip())
                    category = Category(name=predicted_name, slug=slug)
                    db.add(category)
                    db.flush()
                book.category_id = category.id
                filled['category_predicted'] = predicted_name

        # 3. Keywords — generate from summary
        if not book.keywords:
            predicted_keywords = self._predict_keywords(summary, language)
            if predicted_keywords:
                book.keywords = predicted_keywords
                filled['keywords_set'] = True

        return filled

    def _predict_category(self, summary: str, language: str) -> Optional[str]:
        categories_list = "\n".join(f"- {c}" for c in PREDEFINED_CATEGORIES)
        prompt_template = _CATEGORY_PROMPTS.get(language, _CATEGORY_PROMPTS['ar'])
        prompt = prompt_template.format(categories=categories_list, summary=summary[:1000])
        result = self._call_llm(prompt)
        if not result:
            return None
        result = result.strip()
        # Exact match first
        if result in PREDEFINED_CATEGORIES:
            return result
        # Partial match fallback (LLM sometimes adds punctuation)
        for cat in PREDEFINED_CATEGORIES:
            if cat in result:
                return cat
        logger.warning(f"LLM returned unknown category '{result}' — skipping")
        return None

    def _predict_keywords(self, summary: str, language: str) -> Optional[str]:
        prompt_template = _KEYWORDS_PROMPTS.get(language, _KEYWORDS_PROMPTS['ar'])
        prompt = prompt_template.format(summary=summary[:1000])
        result = self._call_llm(prompt)
        return result.strip() if result else None

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Send a prompt to the DeepSeek API and return the response text."""
        try:
            response = httpx.post(
                f"{settings.SUMMARIZATION_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.SUMMARIZATION_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.3,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None
