---
description: Create a new project from the Vibe Coding template
---

# New Project Workflow

Creates a new project by cloning the template, customizing it, and setting up a new GitHub repo.

// turbo-all

## Prerequisites
- GitHub CLI authenticated (`gh auth status`)
- Git configured with your user

## Steps

### 1. Create project directory
Replace `PROJECT_NAME` with your actual project name (use kebab-case, e.g., `weather-bot`):

```powershell
$PROJECT_NAME = "my-new-project"
# Recommended: Create inside the Projects/ directory of the root workspace
$PROJECT_DIR = "C:\Users\jared\Vibe Coding (root)\Projects\$PROJECT_NAME"
```

### 2. Clone the template (shallow, no git history)
```powershell
git clone --depth 1 https://github.com/JMCJDog/Vibe-Coding--root-.git $PROJECT_DIR
```

### 3. Remove old git history and reinitialize
```powershell
Remove-Item -Recurse -Force "$PROJECT_DIR\.git"
Set-Location $PROJECT_DIR
git init
git add -A
git commit -m "Initial commit from Vibe Coding template"
```

### 4. Update project metadata
Edit these files with your new project name:
- `setup.cfg` - change `name = vibe_coding` to your project name
- `README.md` - update title and description
- `src/app/main.py` - update FastAPI title/description

### 5. Create GitHub repository and push
```powershell
gh repo create $PROJECT_NAME --public --source=. --remote=origin --push
```

### 6. Verify
```powershell
gh repo view --web
```

## Customization Checklist
After creating the project, update:
- [ ] `setup.cfg` - project name, version, description
- [ ] `README.md` - project title, description, badges
- [ ] `src/app/main.py` - FastAPI metadata
- [ ] `.github/workflows/ci.yml` - Docker image name if needed

## Example Usage
To create a project called "weather-api" inside Projects/:
```powershell
# Run in PowerShell
$PROJECT_NAME = "weather-api"
$PROJECT_DIR = "C:\Users\jared\Vibe Coding (root)\Projects\$PROJECT_NAME"
git clone --depth 1 https://github.com/JMCJDog/Vibe-Coding--root-.git $PROJECT_DIR
cd $PROJECT_DIR
Remove-Item -Recurse -Force .git
git init
git add -A
git commit -m "Initial commit from Vibe Coding template"
gh repo create $PROJECT_NAME --public --source=. --remote=origin --push
```
