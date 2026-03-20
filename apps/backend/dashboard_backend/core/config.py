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

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
