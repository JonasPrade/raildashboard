import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Select the correct .env file depending on the environment
# env_file = '.env.test' if os.getenv("ENVIRONMENT") == 'test' else '.env'

class Settings(BaseSettings):
    # Explicitly map environment variable names for clarity
    database_url: str  # expects DATABASE_URL in .env
    environment: str = "development"
    debug: bool = False
    rinf_api_url: str
    rinf_username: str
    rinf_password: str
    routing_base_url: str = "http://localhost:8989"
    routing_timeout_seconds: float = 20.0
    graph_version: str = "unknown"

    model_config = SettingsConfigDict(
        env_file=f".env{'.' + os.getenv('ENVIRONMENT') if os.getenv('ENVIRONMENT') else ''}",
        case_sensitive=False
    )

settings = Settings()
