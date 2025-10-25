"""Configuration file validation tests."""
import configparser
import pathlib
import tomli


def test_pytest_configuration_valid() -> None:
    """Verify pytest.ini exists and is valid."""
    project_root = pathlib.Path(__file__).parent.parent
    pytest_ini = project_root / "pytest.ini"

    assert pytest_ini.exists(), "pytest.ini must exist"

    config = configparser.ConfigParser()
    config.read(pytest_ini)

    assert "pytest" in config, "pytest.ini must have [pytest] section"

    # Verify required settings
    pytest_config = config["pytest"]
    assert "testpaths" in pytest_config, "pytest.ini must specify testpaths"
    assert "tests" in pytest_config["testpaths"], "testpaths must include 'tests'"


def test_coverage_configuration_valid() -> None:
    """Verify .coveragerc exists and is valid."""
    project_root = pathlib.Path(__file__).parent.parent
    coveragerc = project_root / ".coveragerc"

    assert coveragerc.exists(), ".coveragerc must exist"

    config = configparser.ConfigParser()
    config.read(coveragerc)

    assert "run" in config, ".coveragerc must have [run] section"
    assert "report" in config, ".coveragerc must have [report] section"


def test_pyproject_toml_valid() -> None:
    """Verify pyproject.toml exists and is valid TOML."""
    project_root = pathlib.Path(__file__).parent.parent
    pyproject = project_root / "pyproject.toml"

    assert pyproject.exists(), "pyproject.toml must exist"

    # Parse TOML to verify it's valid
    with open(pyproject, "rb") as f:
        config = tomli.load(f)

    assert "tool" in config, "pyproject.toml must have [tool] section"


def test_readme_exists() -> None:
    """Verify README.md exists."""
    project_root = pathlib.Path(__file__).parent.parent
    readme = project_root / "README.md"

    assert readme.exists(), "README.md must exist"
    assert readme.is_file(), "README.md must be a file"

    content = readme.read_text()
    assert len(content) > 100, "README.md must have substantial content"
    assert "# Hello World API" in content, "README.md must have project title"


def test_requirements_files_exist() -> None:
    """Verify requirements files exist."""
    project_root = pathlib.Path(__file__).parent.parent

    requirements = project_root / "requirements.txt"
    assert requirements.exists(), "requirements.txt must exist"

    requirements_dev = project_root / "requirements-dev.txt"
    assert requirements_dev.exists(), "requirements-dev.txt must exist"
