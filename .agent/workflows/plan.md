---
description: Create a structured plan before implementing a feature
---

# Plan Workflow

Creates a structured planning document before coding to capture goals, constraints, and approach.

// turbo-all

## When to Use
- Before starting any non-trivial feature
- When requirements are unclear or complex
- When coordinating changes across multiple files

## Steps

### 1. Create Planning Document
Create `PLAN.md` in the project root (or `Sandbox/` for experiments):

```markdown
# Feature: [Feature Name]

## Goal
What are we trying to achieve?

## Scope
- [ ] In scope: ...
- [ ] Out of scope: ...

## Approach
How will we implement this?

## Files to Modify
- `src/app/...`
- `tests/...`

## Edge Cases
- ...

## Verification
How will we know it works?
```

### 2. Review Existing Code
Before implementing, understand the codebase:
```powershell
# Find related files
Get-ChildItem -Recurse -Filter "*.py" | Select-String "pattern"
```

### 3. Document Decisions
Update `PLAN.md` with any decisions made during discussion.

### 4. Proceed to Implementation
Once the plan is solid, begin coding. Refer back to `PLAN.md` to stay on track.

## After Implementation
- Run `/verify` to confirm the feature works
- Archive or delete `PLAN.md` if no longer needed
