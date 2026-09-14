"""
Application configuration.

All configuration is sourced from environment variables (optionally loaded
from a local .env file for development). See .env.example for the full
list of supported variables and safe placeholder values.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_name: str = "Lenny Growth Assistant"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/lenny_growth_assistant"
    )
    # Dedicated database for the automated test suite. Kept separate from
    # database_url so running tests can never touch development data.
    test_database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/lenny_growth_assistant_test"
    )

    # CORS - comma-separated list of allowed origins for local frontend dev
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # RAG / embeddings — Ollama is used for embeddings regardless of which
    # provider answers a given chat (see app/rag/embeddings.py).
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    # Chat generation model, distinct from the embedding model above — the
    # two are not interchangeable (see app/providers/ollama.py).
    ollama_chat_model: str = "phi3:latest"

    # Path to the transcript corpus, relative to the project root (the
    # parent of this backend/ directory) unless given as an absolute path.
    transcripts_dir: str = "data/transcripts"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so the environment is only parsed once."""
    return Settings()
