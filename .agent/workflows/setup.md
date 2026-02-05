---
description: Install dependencies and setup project
---

# Setup Workflow

// turbo-all

1. Create virtual environment:
```powershell
python -m venv .venv
```

2. Activate venv:
```powershell
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:
```powershell
.\.venv\Scripts\pip.exe install -e . -c Resources/constraints.txt
```

4. Verify installation:
```powershell
.\.venv\Scripts\python.exe -c "from app.main import app; print('Setup OK')"
```
