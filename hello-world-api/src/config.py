"""Configuration module with Pydantic Settings validation."""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable validation."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    SECRET_KEY: str
    DEBUG: bool = False
    DATABASE_URL: Optional[str] = None
    API_KEY: Optional[str] = None


settings = Settings()
