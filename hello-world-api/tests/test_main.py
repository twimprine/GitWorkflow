"""Main application tests."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_app_instance_exists() -> None:
    """Verify FastAPI app instance exists."""
    from src.main import app

    assert app is not None
    assert isinstance(app, FastAPI)


def test_app_title() -> None:
    """Verify app has correct title."""
    from src.main import app

    assert app.title == "Hello World API"


def test_app_version() -> None:
    """Verify app has correct version."""
    from src.main import app

    assert app.version == "1.0.0"


def test_root_endpoint() -> None:
    """Test root endpoint returns correct message."""
    from src.main import app

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


@pytest.mark.asyncio
async def test_root_endpoint_async() -> None:
    """Test root endpoint async function directly."""
    from src.main import root

    result = await root()

    assert result == {"message": "Hello World"}
    assert isinstance(result, dict)
    assert "message" in result
