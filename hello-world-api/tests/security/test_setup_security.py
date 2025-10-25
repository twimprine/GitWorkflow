"""Security validation tests for project setup."""
import os
import pathlib
from typing import List


def test_no_secrets_in_config_files() -> None:
    """Verify no real secrets exist in configuration files."""
    project_root = pathlib.Path(__file__).parent.parent.parent

    # Check .env.example doesn't contain real secrets
    env_example = project_root / ".env.example"
    assert env_example.exists(), ".env.example must exist"

    content = env_example.read_text()

    # Prohibited patterns that indicate real secrets
    prohibited_patterns = [
        "sk-",  # OpenAI API keys
        "ghp_",  # GitHub personal access tokens
        "gho_",  # GitHub OAuth tokens
        "AKIA",  # AWS access keys
        "-----BEGIN",  # Private keys
    ]

    for pattern in prohibited_patterns:
        assert pattern not in content, f"Real secret pattern '{pattern}' found in .env.example"

    # Must contain placeholder text
    assert "your-secret-key-here" in content or "change-in-production" in content


def test_gitignore_excludes_sensitive_files() -> None:
    """Verify .gitignore properly excludes sensitive files."""
    project_root = pathlib.Path(__file__).parent.parent.parent
    gitignore_path = project_root / ".gitignore"

    assert gitignore_path.exists(), ".gitignore must exist"

    content = gitignore_path.read_text()

    # Required patterns in .gitignore
    required_patterns = [
        ".env",
        "*.pem",
        "*.key",
        "secrets.json",
        "credentials.json",
        "venv/",
        "__pycache__/",
    ]

    for pattern in required_patterns:
        assert pattern in content, f"Required pattern '{pattern}' missing from .gitignore"


def test_env_example_has_no_real_secrets() -> None:
    """Verify .env.example contains only placeholder values."""
    project_root = pathlib.Path(__file__).parent.parent.parent
    env_example = project_root / ".env.example"

    assert env_example.exists(), ".env.example must exist"

    content = env_example.read_text()
    lines = content.split("\n")

    for line in lines:
        if line.strip() and not line.strip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip()

            # Check for real secret indicators
            assert len(value) < 100, f"{key} value too long, might be real secret"
            assert not value.startswith("sk-"), f"{key} looks like real API key"
            assert not value.startswith("ghp_"), f"{key} looks like real GitHub token"


def test_virtual_env_not_committed() -> None:
    """Verify virtual environment directories are excluded from git."""
    project_root = pathlib.Path(__file__).parent.parent.parent
    gitignore_path = project_root / ".gitignore"

    assert gitignore_path.exists(), ".gitignore must exist"

    content = gitignore_path.read_text()

    venv_patterns = ["venv/", ".venv/", "env/", "ENV/"]

    for pattern in venv_patterns:
        assert pattern in content, f"Virtual env pattern '{pattern}' must be in .gitignore"


def test_dependency_versions_pinned() -> None:
    """Verify all dependencies have pinned versions for security."""
    project_root = pathlib.Path(__file__).parent.parent.parent
    requirements = project_root / "requirements.txt"

    assert requirements.exists(), "requirements.txt must exist"

    content = requirements.read_text()
    lines = [line.strip() for line in content.split("\n") if line.strip() and not line.startswith("#")]

    for line in lines:
        # Each dependency must have exact version pinning (==)
        assert "==" in line, f"Dependency '{line}' must use exact version pinning (==)"

        # Extract package and version
        if "==" in line:
            package, version = line.split("==")
            assert version.strip(), f"Package '{package}' has empty version"
