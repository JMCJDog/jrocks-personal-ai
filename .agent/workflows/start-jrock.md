---
description: Start JRock's Personal AI (Backend, Frontend, and Browser)
---

# Start JRock Personal AI

// turbo-all

1. Start the Backend Server (Term 1):
```powershell
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Start the Frontend Server (Term 2):
```powershell
cd frontend; npm run dev
```

3. Open the Application in Browser:
```powershell
Start-Process "http://localhost:3000"
```
