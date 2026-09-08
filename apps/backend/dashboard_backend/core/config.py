import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str | None:
    """Walk up from this file to find a .env file (works both locally and in Docker).
    In Docker the env vars are injected directly, so no .env file will be found
    and pydantic-settings falls back to reading from the process environment."""
    suffix = f".{os.getenv('ENVIRONMENT')}" if os.getenv('ENVIRONMENT') else ""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / f".env{suffix}"
        if candidate.exists():
            return str(candidate)
    return None


class Settings(BaseSettings):
    # Explicitly map environment variable names for clarity
    database_url: str  # expects DATABASE_URL in .env
    # SQLAlchemy connection pool (see database.py). Keep pool_size + max_overflow
    # per uvicorn worker below the Postgres max_connections budget.
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle_seconds: int = 1800
    environment: str = "development"
    debug: bool = False
    rinf_api_url: Optional[str] = None
    rinf_username: Optional[str] = None
    rinf_password: Optional[str] = None
    osm_pbf_dir: Path = Path("data/osm")
    routing_base_url: str = "http://localhost:8989"
    routing_timeout_seconds: float = 20.0
    graph_version: str = "unknown"
    backend_cors_origins: list[str] = ["http://localhost:5173"]
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    session_secret_key: str  # Required: 32-byte hex string for HMAC-signing session tokens
    upload_dir: str = "/app/uploads/text-attachments"  # UPLOAD_DIR env var
    # LLM settings for optional VIB semantic extraction (OpenAI-compatible)
    # llm_base_url empty = feature disabled
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # OCR settings for VIB PDF text extraction (Mistral OCR API)
    # ocr_api_key empty = pymupdf fallback is used instead
    ocr_api_key: str = ""
    ocr_base_url: str = "https://api.mistral.ai"
    ocr_model: str = "mistral-ocr-latest"
    # Strip repeated header/footer lines (page numbers, running headers) from OCR output.
    # Can be overridden per-import via the upload form.
    ocr_strip_headers_footers: bool = True

    # Haushalt import: run the shared OCR stage over the PDF as well, so the run
    # stores the same machine-readable document text as VIB/Fulda. Off by default —
    # the table values always come from pdfplumber either way, so OCR only adds
    # cost per import. Turning it on does not change any imported number.
    haushalt_ocr_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
