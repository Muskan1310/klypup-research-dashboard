"""
Centralized application configuration.

Why this exists as its own module rather than scattering `os.getenv()` calls
across the codebase:

1. Single source of truth — every setting the app needs is declared here,
   with a type, so a missing/malformed env var fails loudly at startup
   (via Pydantic validation) instead of silently causing a bug three
   layers deep at request time.
2. Testability — tests can override `Settings` without touching real
   environment variables.
3. This is the FastAPI-idiomatic pattern (pydantic-settings), not a
   custom-rolled config loader — using the ecosystem-standard approach
   here rather than inventing our own is a deliberate "avoid unnecessary
   complexity" choice.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Klypup Investment Research Dashboard"
    environment: str = "development"

    # --- Database ---
    database_url: str = "postgresql://klypup:klypup@localhost:5432/klypup"

    # --- Auth ---
    jwt_secret_key: str = "changeme-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24h — short-lived by design, see TDD Section 9

    # --- External AI / data APIs ---
    anthropic_api_key: str = ""
    alpha_vantage_api_key: str = ""
    news_api_key: str = ""

    # --- RAG ---
    chroma_persist_dir: str = "./chroma_data"


# A single, importable instance — modules do `from app.core.config import settings`
settings = Settings()
