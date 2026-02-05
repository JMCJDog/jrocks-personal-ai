---
description: Structured debugging workflow for tracking down issues
---

# Debug Workflow

Systematic approach to finding and fixing bugs.

// turbo-all

## When to Use
- When tests are failing
- When encountering runtime errors
- When behavior doesn't match expectations

## Steps

### 1. Collect Error Context
Gather the full error including stack trace:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v --tb=long 2>&1 | Out-File debug_output.txt
```

### 2. Identify the Error Location
```powershell
# View the error output
Get-Content debug_output.txt | Select-Object -Last 50
```

Key info to extract:
- **File**: Which file threw the error?
- **Line**: What line number?
- **Error Type**: `TypeError`, `ValueError`, `KeyError`, etc.?
- **Message**: What does the error say?

### 3. Analyze Root Cause
Common patterns:
| Error Type | Likely Cause |
|------------|--------------|
| `ImportError` | Missing dependency or wrong path |
| `TypeError` | Wrong argument type or count |
| `KeyError` | Missing dict key or env var |
| `AttributeError` | Wrong object type or typo |
| `AssertionError` | Test expectation not met |

### 4. Form Hypothesis
Before changing code, state:
> "I believe the issue is [X] because [Y]. I'll verify by [Z]."

### 5. Apply Fix
Make the minimal change needed to fix the issue.

### 6. Verify Fix
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

### 7. Clean Up
```powershell
Remove-Item debug_output.txt -ErrorAction SilentlyContinue
```

## Debugging Tips
- **Reproduce first**: Can you trigger the bug reliably?
- **Isolate**: Run just the failing test with `-k test_name`
- **Print debug**: Add temporary `print()` statements if needed
- **Check inputs**: Are function arguments what you expect?
