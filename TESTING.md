# Testing Guide

This document describes the testing workflow for Vibe Coding.

## Quick Test Command

```powershell
make test
```

## Manual Test Commands

Activate virtual environment first:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Run All Tests
```powershell
python -m pytest tests/ -v
```

### Run Specific Test File
```powershell
python -m pytest tests/test_health.py -v
```

### Run with Coverage
```powershell
python -m pytest tests/ --cov=app --cov-report=html
```

## Test Structure

```
tests/
├── test_health.py    # API endpoint tests
└── conftest.py       # Shared fixtures (add as needed)
```

## Writing New Tests

1. Create test file: `tests/test_<feature>.py`
2. Import the test client:
   ```python
   from fastapi.testclient import TestClient
   from app.main import app
   
   client = TestClient(app)
   ```
3. Write test functions prefixed with `test_`:
   ```python
   def test_my_feature():
       response = client.get("/my-endpoint")
       assert response.status_code == 200
   ```

## CI Integration

Tests run automatically on:
- Push to `main` branch
- Pull requests to `main`

See `.github/workflows/ci.yml` for CI configuration.
