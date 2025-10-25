"""Dependency validation tests."""
import importlib
import pathlib
import subprocess
import sys


def test_production_dependencies_installed() -> None:
    """Verify all production dependencies are installed."""
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic_settings",
        "slowapi",
        "dateutil",
    ]

    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            assert False, f"Production dependency '{package}' not installed"


def test_development_dependencies_installed() -> None:
    """Verify all development dependencies are installed."""
    required_packages = [
        "pytest",
        "pytest_asyncio",
        "pytest_cov",
        "pytest_benchmark",
        "httpx",
        "black",
        "ruff",
        "mypy",
    ]

    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            assert False, f"Development dependency '{package}' not installed"


def test_no_dependency_conflicts() -> None:
    """Verify no dependency conflicts exist."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"Dependency conflicts found:\n{result.stdout}\n{result.stderr}"
    except subprocess.TimeoutExpired:
        assert False, "pip check timed out"


def test_fastapi_version_secure() -> None:
    """Verify FastAPI version is >= 0.115.12 (fixes CVE-2024-24762)."""
    import fastapi

    version_parts = fastapi.__version__.split(".")
    major = int(version_parts[0])
    minor = int(version_parts[1])
    patch = int(version_parts[2]) if len(version_parts) > 2 else 0

    # Must be >= 0.115.12
    assert major > 0 or (major == 0 and minor > 115) or (major == 0 and minor == 115 and patch >= 12), \
        f"FastAPI version {fastapi.__version__} is vulnerable. Must be >= 0.115.12 (CVE-2024-24762)"
