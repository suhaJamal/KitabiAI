
"""
Application configuration (12-factor style).

- Defines Settings (using pydantic-settings) for env-driven config.
- Includes Azure Document Intelligence credentials for Arabic processing.
- Central place to add future settings: limits, OCR policy, storage, etc.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "KitabiAI - Unified (English & Arabic)"

    # Database
    DATABASE_URL: str  # PostgreSQL connection string
    
    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: str  # Blob storage connection
    AZURE_STORAGE_CONTAINER_HTML: str = "books-html"
    AZURE_STORAGE_CONTAINER_MARKDOWN: str = "books-markdown"
    AZURE_STORAGE_CONTAINER_JSON: str = "books-json"
    AZURE_STORAGE_CONTAINER_PDF: str = "books-pdf"
    AZURE_STORAGE_CONTAINER_IMAGES: str = "books-images"

    # Azure Document Intelligence
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = None
    AZURE_DOCUMENT_INTELLIGENCE_KEY: Optional[str] = None

    # Feature flags
    USE_AZURE_FOR_ARABIC: bool = True #  Controls whether to use Azure Document Intelligence for Arabic text extraction.
    ARABIC_RATIO_THRESHOLD: float = 0.3 #Minimum percentage of Arabic characters required to classify a document as "Arabic".
    MIN_BOOKMARKS_OK: int = 4 # Minimum number of PDF bookmarks required to trust bookmark-based TOC extraction.

    # FastText Language Detection (Cost Optimization)
    USE_FASTTEXT_DETECTION: bool = True  # Use FastText for quick language detection
    FASTTEXT_MODEL_PATH: str = "lid.176.ftz"  # Path to FastText model
    FASTTEXT_CONFIDENCE_THRESHOLD: float = 0.5  # Min confidence (0.0-1.0)
    FASTTEXT_SAMPLE_PAGES: int = 15  # Number of pages to sample for detection

    # Tracing
    ENABLE_TRACING: bool = False  # Set to True to enable and run tracing.py or uncomment # tracer = setup_tracing(app) in the main.py 
    JAEGER_ENDPOINT: str = "http://localhost:4317"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
