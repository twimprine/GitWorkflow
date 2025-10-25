# Hello World API

FastAPI-based Hello World API for PRP workflow validation.

## Security Setup

### Environment Variables
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill in required secrets in `.env` (NEVER commit .env file)
3. Verify environment with:
   ```bash
   python -c "from src.config import settings; print('OK')"
   ```

### Dependency Security
Run security scans before commits:
```bash
pip-audit --strict
safety check
bandit -r src/
```

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify installation
pytest --version
python -c "import fastapi; print(fastapi.__version__)"
```

## Testing

```bash
# Run all tests with coverage
pytest

# Run security tests only
pytest tests/security/

# Run with coverage report
pytest --cov=src --cov-report=html
```

## Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Project Structure

- `src/`: Application source code
  - `routers/`: API route handlers
  - `models/`: Data models
  - `middleware/`: Custom middleware
  - `config.py`: Environment configuration
  - `main.py`: Application entry point
- `tests/`: Test suite
  - `security/`: Security validation tests
  - `conftest.py`: Pytest fixtures
- `docs/`: Documentation

## Security Considerations

- All dependencies are pinned for reproducibility
- FastAPI updated to >=0.115.12 (fixes CVE-2024-24762)
- Environment variables validated with Pydantic Settings
- Secrets never committed to git (.gitignore configured)
- Regular security scanning with pip-audit and safety

## Next Steps

See PRP-HELLO-WORLD-API-001-a-002 for core implementation.
