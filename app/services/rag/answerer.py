# app/services/rag/answerer.py
"""
Generate answers from retrieved sections using GPT-4o-mini.

Builds a grounded prompt from the top-K retrieved sections and
returns an answer with source citations (section title + page range).
"""

import logging
from typing import Optional
from openai import OpenAI

from ...core.config import settings

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"

_PROMPTS = {
    'ar': (
        "أنت مساعد متخصص في الإجابة عن أسئلة الكتب. "
        "أجب عن السؤال التالي بناءً فقط على المقاطع المستخرجة من كتاب \"{book_title}\".\n\n"
        "المقاطع:\n{context}\n\n"
        "السؤال: {question}\n\n"
        "أجب باللغة العربية بشكل مختصر ومفيد. "
        "إذا لم تجد الإجابة في المقاطع، قل ذلك بوضوح."
    ),
    'en': (
        "You are an assistant specialized in answering questions about books. "
        "Answer the following question based only on the passages extracted from \"{book_title}\".\n\n"
        "Passages:\n{context}\n\n"
        "Question: {question}\n\n"
        "Answer concisely and helpfully in English. "
        "The passages may be in Arabic — read them and answer in English regardless. "
        "If you can't find the answer in the passages, say so clearly."
    ),
}

_NO_ANSWER = {
    'ar': "لم أجد في هذا الكتاب معلومات كافية للإجابة على سؤالك.",
    'en': "I couldn't find enough information in this book to answer your question.",
}

_MAX_SOURCES = 4  # max unique sections shown in the sources list


class Answerer:

    def __init__(self):
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured in .env")
        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def answer(
        self,
        question: str,
        sections: list,
        book_title: str,
        language: str,
        question_language: str = None,
    ) -> dict:
        """
        Generate an answer with source citations.

        Returns:
            { "answer": str, "sources": [{ "section", "pages", "book" }] }
        """
        # Response language follows the question, not the book
        response_lang = question_language or language

        if not sections:
            return {"answer": _NO_ANSWER.get(response_lang, _NO_ANSWER['en']), "sources": []}

        context_parts = []
        seen_titles = {}  # title -> best-similarity source entry (for deduplication)

        for i, sec in enumerate(sections, 1):
            snippet = sec.get("content") or sec.get("summary") or ""
            if not snippet:
                continue

            # All chunks feed the LLM context for the best possible answer
            context_parts.append(f"[{i}] {sec['title']}:\n{snippet}")

            # Deduplicate sources by section title — keep the highest-similarity entry
            title = sec["title"]
            if title not in seen_titles or sec.get("similarity", 0) > seen_titles[title]["similarity"]:
                seen_titles[title] = {
                    "section":    title,
                    "pages":      f"{sec['page_start']}-{sec['page_end']}",
                    "book":       sec["book_title"],
                    "similarity": sec.get("similarity", 0),
                }

        if not context_parts:
            return {"answer": _NO_ANSWER.get(language, _NO_ANSWER['ar']), "sources": []}

        # Show only top-N unique sections ranked by similarity — strip internal score
        ranked = sorted(seen_titles.values(), key=lambda x: x["similarity"], reverse=True)
        sources = [
            {"section": s["section"], "pages": s["pages"], "book": s["book"]}
            for s in ranked[:_MAX_SOURCES]
        ]

        context = "\n\n".join(context_parts)
        prompt_template = _PROMPTS.get(response_lang, _PROMPTS['en'])
        prompt = prompt_template.format(
            book_title=book_title,
            context=context,
            question=question,
        )

        answer_text = self._call_llm(prompt)
        return {
            "answer": answer_text or _NO_ANSWER.get(response_lang, _NO_ANSWER['en']),
            "sources": sources,
        }

    def _call_llm(self, prompt: str) -> Optional[str]:
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Answerer LLM call failed: {e}")
            return None
