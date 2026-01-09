"""
Local file storage service for Phase 1 testing.

Saves generated files (HTML, Markdown, JSONL) to local outputs/ folder
and returns file:// URLs for database storage.
"""

import os
from pathlib import Path
from typing import Dict
from datetime import datetime

class LocalStorageService:
    """Service for saving files locally and generating file URLs."""

    def __init__(self, base_output_dir: str = "outputs/books"):
        """
        Initialize local storage service.

        Args:
            base_output_dir: Base directory for storing book files
        """
        self.base_output_dir = Path(base_output_dir)

    def _get_book_dir(self, book_id: int) -> Path:
        """Get the directory path for a specific book."""
        book_dir = self.base_output_dir / str(book_id)
        book_dir.mkdir(parents=True, exist_ok=True)
        return book_dir

    def _generate_file_url(self, file_path: Path) -> str:
        """
        Generate a file:// URL from a local file path.

        Args:
            file_path: Path to the local file

        Returns:
            file:// URL string
        """
        # Convert to absolute path and then to file URL
        abs_path = file_path.resolve()
        # Use as_uri() for proper file:// URL format
        return abs_path.as_uri()

    def save_html(self, book_id: int, content: str, filename: str = None) -> str:
        """
        Save HTML content to local file.

        Args:
            book_id: Database book ID
            content: HTML content
            filename: Optional custom filename (default: book.html)

        Returns:
            file:// URL to the saved file
        """
        book_dir = self._get_book_dir(book_id)
        file_name = filename or "book.html"
        file_path = book_dir / file_name

        file_path.write_text(content, encoding='utf-8')
        return self._generate_file_url(file_path)

    def save_markdown(self, book_id: int, content: str, filename: str = None) -> str:
        """
        Save Markdown content to local file.

        Args:
            book_id: Database book ID
            content: Markdown content
            filename: Optional custom filename (default: book.md)

        Returns:
            file:// URL to the saved file
        """
        book_dir = self._get_book_dir(book_id)
        file_name = filename or "book.md"
        file_path = book_dir / file_name

        file_path.write_text(content, encoding='utf-8')
        return self._generate_file_url(file_path)

    def save_pages_jsonl(self, book_id: int, content: str, filename: str = None) -> str:
        """
        Save pages JSONL content to local file.

        Args:
            book_id: Database book ID
            content: JSONL content (page-level analysis)
            filename: Optional custom filename (default: pages.jsonl)

        Returns:
            file:// URL to the saved file
        """
        book_dir = self._get_book_dir(book_id)
        file_name = filename or "pages.jsonl"
        file_path = book_dir / file_name

        file_path.write_text(content, encoding='utf-8')
        return self._generate_file_url(file_path)

    def save_sections_jsonl(self, book_id: int, content: str, filename: str = None) -> str:
        """
        Save sections JSONL content to local file.

        Args:
            book_id: Database book ID
            content: JSONL content (TOC sections)
            filename: Optional custom filename (default: sections.jsonl)

        Returns:
            file:// URL to the saved file
        """
        book_dir = self._get_book_dir(book_id)
        file_name = filename or "sections.jsonl"
        file_path = book_dir / file_name

        file_path.write_text(content, encoding='utf-8')
        return self._generate_file_url(file_path)

    def save_pdf(self, book_id: int, pdf_bytes: bytes, filename: str = None) -> str:
        """
        Save PDF file to local storage.

        Args:
            book_id: Database book ID
            pdf_bytes: PDF file content as bytes
            filename: Optional custom filename (default: book.pdf)

        Returns:
            file:// URL to the saved file
        """
        book_dir = self._get_book_dir(book_id)
        file_name = filename or "book.pdf"
        file_path = book_dir / file_name

        file_path.write_bytes(pdf_bytes)
        return self._generate_file_url(file_path)

    def save_cover_image(self, book_id: int, image_bytes: bytes, filename: str = None) -> str:
        """
        Save cover image to local storage.

        Args:
            book_id: Database book ID
            image_bytes: Image file content as bytes
            filename: Optional custom filename (default: cover.jpg)

        Returns:
            file:// URL to the saved file
        """
        book_dir = self._get_book_dir(book_id)
        file_name = filename or "cover.jpg"
        file_path = book_dir / file_name

        file_path.write_bytes(image_bytes)
        return self._generate_file_url(file_path)

    def save_all_generated_files(
        self,
        book_id: int,
        html_content: str = None,
        markdown_content: str = None,
        pages_jsonl_content: str = None,
        sections_jsonl_content: str = None
    ) -> Dict[str, str]:
        """
        Save all generated files at once.

        Args:
            book_id: Database book ID
            html_content: HTML content (optional)
            markdown_content: Markdown content (optional)
            pages_jsonl_content: Pages JSONL content (optional)
            sections_jsonl_content: Sections JSONL content (optional)

        Returns:
            Dictionary with keys: html_url, markdown_url, pages_jsonl_url, sections_jsonl_url
            (values are None if content not provided)
        """
        urls = {
            'html_url': None,
            'markdown_url': None,
            'pages_jsonl_url': None,
            'sections_jsonl_url': None
        }

        if html_content:
            urls['html_url'] = self.save_html(book_id, html_content)

        if markdown_content:
            urls['markdown_url'] = self.save_markdown(book_id, markdown_content)

        if pages_jsonl_content:
            urls['pages_jsonl_url'] = self.save_pages_jsonl(book_id, pages_jsonl_content)

        if sections_jsonl_content:
            urls['sections_jsonl_url'] = self.save_sections_jsonl(book_id, sections_jsonl_content)

        return urls


# Global instance
local_storage = LocalStorageService()
