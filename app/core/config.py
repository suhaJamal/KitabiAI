
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

    # Azure Document Intelligence
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = None
    AZURE_DOCUMENT_INTELLIGENCE_KEY: Optional[str] = None

    # Feature flags
    USE_AZURE_FOR_ARABIC: bool = True
    ARABIC_RATIO_THRESHOLD: float = 0.3
    MIN_BOOKMARKS_OK: int = 4

    # FastText Language Detection (Cost Optimization)
    USE_FASTTEXT_DETECTION: bool = True  # Use FastText for quick language detection
    FASTTEXT_MODEL_PATH: str = "lid.176.ftz"  # Path to FastText model
    FASTTEXT_CONFIDENCE_THRESHOLD: float = 0.5  # Min confidence (0.0-1.0)
    FASTTEXT_SAMPLE_PAGES: int = 10  # Number of pages to sample for detection

    # Tracing
    ENABLE_TRACING: bool = False  # Set to True to enable
    JAEGER_ENDPOINT: str = "http://localhost:4317"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
