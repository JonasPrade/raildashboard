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

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / f".env{_ENV_SUFFIX}"),
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
