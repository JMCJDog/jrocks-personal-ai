---
description: Git add, commit, and push workflow
---

# Git Push Workflow

// turbo-all

1. Stage all changes:
```powershell
git add -A
```

2. Check status:
```powershell
git status
```

3. Commit with descriptive message (**REQUIRED** - never use generic messages):
> **IMPORTANT**: Always write a clear, descriptive commit message explaining WHAT changed and WHY.
> Format: `type: brief description` (e.g., `feat: add Next.js reference to requirements`)
> Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
```powershell
git commit -m "type: descriptive message here"
```

4. Push to remote:
```powershell
git push origin master
```

5. Verify push:
```powershell
git log --oneline -n 3
```
