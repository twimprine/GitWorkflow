# Usage Examples

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage with curl](#basic-usage-with-curl)
3. [Python Client Examples](#python-client-examples)
4. [Testing Examples](#testing-examples)
5. [Development Workflow](#development-workflow)
6. [Troubleshooting](#troubleshooting)

## Quick Start

### Start the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run the development server
uvicorn src.main:app --reload

# Server will start at http://localhost:8000
```

### Test the API

```bash
# Simple GET request
curl http://localhost:8000/

# Expected response:
# {"message":"Hello World"}
```

## Basic Usage with curl

### GET Request to Root Endpoint

```bash
# Basic request
curl http://localhost:8000/

# With verbose output
curl -v http://localhost:8000/

# Save response to file
curl http://localhost:8000/ -o response.json

# With headers
curl -H "Accept: application/json" http://localhost:8000/
```

### Access Interactive Documentation

```bash
# Open Swagger UI in browser
xdg-open http://localhost:8000/docs

# Open ReDoc in browser
xdg-open http://localhost:8000/redoc

# Get OpenAPI schema
curl http://localhost:8000/openapi.json | jq .
```

## Python Client Examples

### Using httpx (Async)

```python
import asyncio
import httpx


async def get_hello_world():
    """Fetch greeting from API asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/")
        return response.json()


async def main():
    result = await get_hello_world()
    print(f"Message: {result['message']}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Using httpx (Sync)

```python
import httpx


def get_hello_world():
    """Fetch greeting from API synchronously."""
    response = httpx.get("http://localhost:8000/")
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    result = get_hello_world()
    print(f"Message: {result['message']}")
```

### Using requests

```python
import requests


def get_hello_world():
    """Fetch greeting from API using requests library."""
    response = requests.get("http://localhost:8000/")
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    result = get_hello_world()
    print(f"Message: {result['message']}")
```

### Error Handling

```python
import httpx


async def get_with_error_handling():
    """Fetch greeting with proper error handling."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code}")
        raise
    except httpx.RequestError as e:
        print(f"Request error occurred: {e}")
        raise
```

## Testing Examples

### Run All Tests

```bash
# Run complete test suite
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_main.py

# Run tests matching pattern
pytest -k "test_root"
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open HTML coverage report
xdg-open htmlcov/index.html
```

### Run Security Tests

```bash
# Run security validation tests
pytest tests/security/

# Run dependency security scan
pip-audit --strict

# Run code security scan
bandit -r src/

# Run with all security checks
safety check && bandit -r src/ && pytest tests/security/
```

### Performance Testing

```bash
# Run benchmark tests
pytest --benchmark-only

# Run with benchmark comparison
pytest --benchmark-compare

# Save benchmark results
pytest --benchmark-autosave
```

## Development Workflow

### Complete Development Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Setup environment variables
cp .env.example .env
# Edit .env with your values

# 4. Verify configuration
python -c "from src.config import settings; print('Config OK')"

# 5. Run tests
pytest

# 6. Start development server
uvicorn src.main:app --reload
```

### Code Quality Checks

```bash
# Format code with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type check with mypy
mypy src/

# Run all quality checks
black src/ tests/ && ruff check src/ tests/ && mypy src/
```

### Pre-Commit Workflow

```bash
# Before committing, run:

# 1. Format code
black src/ tests/

# 2. Run linters
ruff check src/ tests/

# 3. Type check
mypy src/

# 4. Run tests
pytest

# 5. Security scan
pip-audit --strict && safety check && bandit -r src/

# 6. Verify everything passes
./verify.sh
```

## Troubleshooting

### Server Won't Start

```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill process on port 8000
kill -9 $(lsof -t -i :8000)

# Start on different port
uvicorn src.main:app --reload --port 8001
```

### Environment Variable Issues

```bash
# Verify .env file exists
ls -la .env

# Check environment variables are loaded
python -c "from src.config import settings; print(settings.model_dump())"

# Re-copy .env.example if needed
cp .env.example .env
```

### Import Errors

```bash
# Verify virtual environment is activated
which python

# Reinstall dependencies
pip install -r requirements.txt

# Check Python path includes src/
python -c "import sys; print(sys.path)"
```

### Test Failures

```bash
# Run tests with verbose output
pytest -vv

# Run specific failing test
pytest tests/test_main.py::test_root_endpoint -vv

# Clear pytest cache
pytest --cache-clear

# Reinstall dependencies and rerun
pip install -r requirements-dev.txt && pytest
```

### Coverage Issues

```bash
# Clean coverage data
rm .coverage
rm -rf htmlcov/

# Run tests with fresh coverage
pytest --cov=src --cov-report=html

# Check which lines are not covered
pytest --cov=src --cov-report=term-missing
```

## Advanced Examples

### Custom Test Client

```python
from fastapi.testclient import TestClient
from src.main import app

# Create test client
client = TestClient(app)

# Make requests
response = client.get("/")
assert response.status_code == 200
assert response.json() == {"message": "Hello World"}
```

### Environment-Specific Configuration

```python
from src.config import Settings

# Override settings for testing
test_settings = Settings(
    SECRET_KEY="test-secret-key",
    DEBUG=True
)

print(f"Debug mode: {test_settings.DEBUG}")
```

### Performance Monitoring

```bash
# Install performance monitoring tools
pip install locust

# Run load test (example - locust not included in current requirements)
# locust -f load_tests.py --host http://localhost:8000
```

## Next Steps

- See [API Documentation](API.md) for detailed endpoint specifications
- See [README.md](../README.md) for setup and installation instructions
- Check the interactive API docs at http://localhost:8000/docs when server is running
