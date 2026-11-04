from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration read from environment variables."""

    database_url: str = "postgresql+psycopg://hybridly:hybridly@db:5432/hybridly"
    test_database_url: str | None = None
    timezone: str = "Europe/Warsaw"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
