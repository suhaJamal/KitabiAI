# app/services/azure_storage_service.py
"""
Azure Blob Storage service for Phase 3.

Uploads files to Azure Blob Storage and returns blob URLs.
Uses separate containers for different file types:
- books-html: HTML files
- books-markdown: Markdown files
- books-json: JSONL files (pages and sections)
- books-pdf: PDF files
- books-images: Cover images
"""

import logging
from pathlib import Path
from typing import Optional
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceExistsError

from ..core.config import settings

logger = logging.getLogger(__name__)


class AzureStorageService:
    """
    Azure Blob Storage service for uploading book files.

    Each file type goes to its own container for better organization:
    - HTML → books-html
    - Markdown → books-markdown
    - JSONL (pages, sections) → books-json
    - PDF → books-pdf
    - Cover images → books-images
    """

    def __init__(self):
        """Initialize Azure Blob Storage client."""
        self.blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )

        # Container names from config
        self.container_html = settings.AZURE_STORAGE_CONTAINER_HTML
        self.container_markdown = settings.AZURE_STORAGE_CONTAINER_MARKDOWN
        self.container_json = settings.AZURE_STORAGE_CONTAINER_JSON
        self.container_pdf = settings.AZURE_STORAGE_CONTAINER_PDF
        self.container_images = settings.AZURE_STORAGE_CONTAINER_IMAGES

    def _upload_blob(
        self,
        container_name: str,
        blob_name: str,
        content: bytes,
        content_type: str
    ) -> str:
        """
        Upload content to Azure Blob Storage.

        Args:
            container_name: Container name (e.g., 'books-html')
            blob_name: Blob name/path (e.g., '1/book.html')
            content: File content as bytes
            content_type: MIME type (e.g., 'text/html')

        Returns:
            Blob URL (e.g., 'https://storage.blob.core.windows.net/books-html/1/book.html')
        """
        try:
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )

            # Set content settings
            content_settings = ContentSettings(content_type=content_type)

            # Upload blob (overwrite if exists)
            blob_client.upload_blob(
                content,
                overwrite=True,
                content_settings=content_settings
            )

            # Return blob URL
            blob_url = blob_client.url
            logger.info(f"Uploaded blob: {blob_url}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to upload blob {blob_name} to {container_name}: {e}")
            raise

    def save_html(self, book_id: int, content: str, filename: str = None) -> str:
        """
        Save HTML content to Azure Blob Storage.

        Args:
            book_id: Database book ID
            content: HTML content string
            filename: Optional filename (default: 'book.html')

        Returns:
            Blob URL
        """
        filename = filename or "book.html"
        blob_name = f"{book_id}/{filename}"
        content_bytes = content.encode('utf-8')

        return self._upload_blob(
            container_name=self.container_html,
            blob_name=blob_name,
            content=content_bytes,
            content_type="text/html; charset=utf-8"
        )

    def save_markdown(self, book_id: int, content: str, filename: str = None) -> str:
        """
        Save Markdown content to Azure Blob Storage.

        Args:
            book_id: Database book ID
            content: Markdown content string
            filename: Optional filename (default: 'book.md')

        Returns:
            Blob URL
        """
        filename = filename or "book.md"
        blob_name = f"{book_id}/{filename}"
        content_bytes = content.encode('utf-8')

        return self._upload_blob(
            container_name=self.container_markdown,
            blob_name=blob_name,
            content=content_bytes,
            content_type="text/markdown; charset=utf-8"
        )

    def save_pages_jsonl(self, book_id: int, content: str, filename: str = None) -> str:
        """
        Save pages JSONL content to Azure Blob Storage.

        Args:
            book_id: Database book ID
            content: JSONL content string
            filename: Optional filename (default: 'book_pages.jsonl')

        Returns:
            Blob URL
        """
        filename = filename or "book_pages.jsonl"
        blob_name = f"{book_id}/{filename}"
        content_bytes = content.encode('utf-8')

        return self._upload_blob(
            container_name=self.container_json,
            blob_name=blob_name,
            content=content_bytes,
            content_type="application/jsonl; charset=utf-8"
        )

    def save_sections_jsonl(self, book_id: int, content: str, filename: str = None) -> str:
        """
        Save sections JSONL content to Azure Blob Storage.

        Args:
            book_id: Database book ID
            content: JSONL content string
            filename: Optional filename (default: 'book_sections.jsonl')

        Returns:
            Blob URL
        """
        filename = filename or "book_sections.jsonl"
        blob_name = f"{book_id}/{filename}"
        content_bytes = content.encode('utf-8')

        return self._upload_blob(
            container_name=self.container_json,
            blob_name=blob_name,
            content=content_bytes,
            content_type="application/jsonl; charset=utf-8"
        )

    def save_pdf(self, book_id: int, pdf_bytes: bytes, filename: str = None) -> str:
        """
        Save PDF file to Azure Blob Storage.

        Args:
            book_id: Database book ID
            pdf_bytes: PDF content as bytes
            filename: Optional filename (default: 'book.pdf')

        Returns:
            Blob URL
        """
        filename = filename or "book.pdf"
        blob_name = f"{book_id}/{filename}"

        return self._upload_blob(
            container_name=self.container_pdf,
            blob_name=blob_name,
            content=pdf_bytes,
            content_type="application/pdf"
        )

    def save_cover_image(self, book_id: int, image_bytes: bytes, filename: str = None) -> str:
        """
        Save cover image to Azure Blob Storage.

        Args:
            book_id: Database book ID
            image_bytes: Image content as bytes
            filename: Optional filename (default: 'cover.jpg')

        Returns:
            Blob URL
        """
        filename = filename or "cover.jpg"
        blob_name = f"{book_id}/{filename}"

        # Detect content type from filename extension
        ext = Path(filename).suffix.lower()
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        content_type = content_type_map.get(ext, 'image/jpeg')

        return self._upload_blob(
            container_name=self.container_images,
            blob_name=blob_name,
            content=image_bytes,
            content_type=content_type
        )


# Global instance
azure_storage = AzureStorageService()
