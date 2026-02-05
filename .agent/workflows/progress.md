---
description: Quick project status check
---

# Progress Workflow

Get a quick overview of project status.

// turbo-all

## Steps

### 1. Git Status
```powershell
git status --short
```

### 2. Recent Commits
```powershell
git log --oneline -n 5
```

### 3. Test Status
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v --tb=no -q
```

### 4. Check for TODOs
```powershell
Select-String -Path "src\**\*.py" -Pattern "TODO|FIXME|HACK" -Recurse | Select-Object -First 10
```

### 5. Summary
Report format:
```
## Project Status
- **Git**: X files modified, Y staged
- **Branch**: master
- **Tests**: X passing, Y failing
- **TODOs**: X items found
```
