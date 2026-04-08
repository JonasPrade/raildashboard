import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Repo root is 4 levels up from this file:
# dashboard_backend/core/config.py -> core -> dashboard_backend -> backend -> apps -> repo root
_REPO_ROOT = Path(__file__).parents[4]
_ENV_SUFFIX = f".{os.getenv('ENVIRONMENT')}" if os.getenv('ENVIRONMENT') else ""

class Settings(BaseSettings):
    # Explicitly map environment variable names for clarity
    database_url: str  # expects DATABASE_URL in .env
    environment: str = "development"
    debug: bool = False
    rinf_api_url: str
    rinf_username: str
    rinf_password: str
    osm_pbf_dir: Path = Path("data/osm")
    routing_base_url: str = "http://localhost:8989"
    routing_timeout_seconds: float = 20.0
    graph_version: str = "unknown"
    backend_cors_origins: list[str] = ["http://localhost:5173"]
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
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

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / f".env{_ENV_SUFFIX}"),
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
