---
description: Run tests with automatic execution
---

# Test Workflow

// turbo-all

1. Activate virtual environment and run pytest:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

2. If tests fail, check specific test output:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v --tb=long
```

3. Run with coverage (optional):
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ --cov=app --cov-report=html
```
