"""Project structure validation tests."""

import pathlib


def test_source_directory_exists() -> None:
    """Verify src/ directory exists."""
    project_root = pathlib.Path(__file__).parent.parent
    src_dir = project_root / "src"

    assert src_dir.exists(), "src/ directory must exist"
    assert src_dir.is_dir(), "src/ must be a directory"


def test_test_directory_exists() -> None:
    """Verify tests/ directory exists."""
    project_root = pathlib.Path(__file__).parent.parent
    tests_dir = project_root / "tests"

    assert tests_dir.exists(), "tests/ directory must exist"
    assert tests_dir.is_dir(), "tests/ must be a directory"


def test_docs_directory_exists() -> None:
    """Verify docs/ directory exists."""
    project_root = pathlib.Path(__file__).parent.parent
    docs_dir = project_root / "docs"

    assert docs_dir.exists(), "docs/ directory must exist"
    assert docs_dir.is_dir(), "docs/ must be a directory"


def test_src_subdirectories_exist() -> None:
    """Verify required src/ subdirectories exist."""
    project_root = pathlib.Path(__file__).parent.parent
    src_dir = project_root / "src"

    required_subdirs = ["routers", "models", "middleware"]

    for subdir in required_subdirs:
        subdir_path = src_dir / subdir
        assert subdir_path.exists(), f"src/{subdir}/ must exist"
        assert subdir_path.is_dir(), f"src/{subdir}/ must be a directory"


def test_package_init_files_exist() -> None:
    """Verify __init__.py files exist for Python packages."""
    project_root = pathlib.Path(__file__).parent.parent

    required_init_files = [
        "src/__init__.py",
        "src/routers/__init__.py",
        "src/models/__init__.py",
        "src/middleware/__init__.py",
        "tests/__init__.py",
        "tests/security/__init__.py",
    ]

    for init_file in required_init_files:
        init_path = project_root / init_file
        assert init_path.exists(), f"{init_file} must exist"
        assert init_path.is_file(), f"{init_file} must be a file"
