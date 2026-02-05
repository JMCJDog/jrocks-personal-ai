---
description: Start development server
---

# Dev Server Workflow

// turbo-all

1. Start the FastAPI dev server:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or using make:
```powershell
make run
```

2. Server will be available at:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
