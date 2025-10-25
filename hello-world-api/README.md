# Hello World API

FastAPI-based Hello World API for PRP workflow validation.

## Overview

A minimal FastAPI application demonstrating secure setup, testing, and documentation practices for the ClaudeAgents PRP workflow system.

**Status**: Phase 1 - Setup Complete
**Version**: 1.0.0
**Python**: 3.13+

## Features

- FastAPI web framework with automatic OpenAPI documentation
- Pydantic Settings for secure environment variable management
- 100% test coverage with pytest
- Security scanning with pip-audit, safety, and bandit
- Code quality tools: black, ruff, mypy
- Performance benchmarking with pytest-benchmark

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.13 or higher
- pip (Python package installer)
- virtualenv or venv
- git (for version control)

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

## Running the Application

### Development Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start the development server with auto-reload
uvicorn src.main:app --reload

# Server will start at http://localhost:8000
```

### Access Documentation

Once the server is running, access the interactive documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### Test the API

```bash
# Simple curl request
curl http://localhost:8000/

# Expected response:
# {"message":"Hello World"}
```

## Security Considerations

- All dependencies are pinned for reproducibility
- FastAPI updated to >=0.115.12 (fixes CVE-2024-24762)
- Environment variables validated with Pydantic Settings
- Secrets never committed to git (.gitignore configured)
- Regular security scanning with pip-audit and safety
- 100% test coverage including security validation tests

## Documentation

- [API Documentation](docs/API.md) - Detailed endpoint specifications
- [Usage Examples](docs/EXAMPLES.md) - Code examples and troubleshooting
- Interactive API Docs - Available at `/docs` when server is running

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run all quality checks:
   ```bash
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   pytest
   ```
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
lsof -i :8000
kill -9 $(lsof -t -i :8000)
```

**Import errors:**
```bash
# Ensure virtual environment is activated
which python
# Should point to venv/bin/python
```

**Test failures:**
```bash
# Clear cache and reinstall
pytest --cache-clear
pip install -r requirements-dev.txt
pytest
```

For more detailed troubleshooting, see [EXAMPLES.md](docs/EXAMPLES.md#troubleshooting).

## License

This project is part of the ClaudeAgents framework for demonstration purposes.

## Related PRPs

- PRP-HELLO-WORLD-API-001-a-001: Initial setup (this phase)
- PRP-HELLO-WORLD-API-001-a-002: Core implementation (next phase)
