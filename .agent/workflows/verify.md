---
description: Verify implementation against plan and run quality checks
---

# Verify Workflow

Post-implementation verification to confirm code works as intended.

// turbo-all

## When to Use
- After completing a feature implementation
- Before committing major changes
- When asked to "fix" something (run before AND after)

## Steps

### 1. Run Tests
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

### 2. Check for Lint Issues
```powershell
.\.venv\Scripts\python.exe -m flake8 src/
```

### 3. Validate Against Plan
If a `PLAN.md` exists, check each item:
- [ ] Does the implementation match the stated goal?
- [ ] Were all in-scope items addressed?
- [ ] Were edge cases handled?

### 4. Quick Smoke Test
```powershell
# Start server briefly to verify it runs
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Visit http://localhost:8000/docs to confirm API is accessible.

### 5. Create Verification Summary
Document what was verified:
```markdown
## Verification Report
- **Tests**: ✅ All passing (X tests)
- **Lint**: ✅ No issues
- **Manual Check**: ✅ API responds correctly
- **Plan Compliance**: ✅ All items addressed
```

## If Issues Found
1. Document the issue
2. Fix the code
3. Re-run this workflow
