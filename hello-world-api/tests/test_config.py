"""Configuration module tests."""

from pathlib import Path

import pytest
from pydantic_settings import BaseSettings


def test_settings_class_exists() -> None:
    """Verify Settings class can be imported."""
    from src.config import Settings

    assert Settings is not None
    assert issubclass(Settings, BaseSettings)


def test_settings_fields_defined() -> None:
    """Verify Settings class has required fields."""
    from src.config import Settings

    fields = Settings.model_fields
    assert "SECRET_KEY" in fields
    assert "DEBUG" in fields
    assert "DATABASE_URL" in fields
    assert "API_KEY" in fields


def test_settings_instance_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Settings can be instantiated from environment variables."""
    from src.config import Settings

    # Set environment variables
    monkeypatch.setenv("SECRET_KEY", "test-secret-123")
    monkeypatch.setenv("DEBUG", "True")

    # Create new settings instance
    settings = Settings()

    assert settings.SECRET_KEY == "test-secret-123"
    assert settings.DEBUG is True


def test_settings_debug_defaults_to_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify DEBUG defaults to False when not set."""
    from src.config import Settings

    monkeypatch.setenv("SECRET_KEY", "test-secret-456")
    monkeypatch.delenv("DEBUG", raising=False)

    # Create a temporary directory without .env file
    monkeypatch.chdir(tmp_path)

    # Use _env_file parameter to override env file loading
    settings = Settings(_env_file=None)

    assert settings.DEBUG is False


def test_settings_optional_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify optional fields can be None."""
    from src.config import Settings

    monkeypatch.setenv("SECRET_KEY", "test-secret-789")

    settings = Settings()

    assert settings.DATABASE_URL is None
    assert settings.API_KEY is None
