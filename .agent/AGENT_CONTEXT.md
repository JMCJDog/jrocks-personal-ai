# Agent Authority Context: Vibe Coding (Root)

## 1. Project Identity & Purpose
**Role**: Master Template & Dev Environment
**Identity**: `Vibe Coding (root)` is a foundational scaffold for local/edge AI applications using Python (FastAPI).
**Primary Goal**: Serve as the *source of truth* and *starting point* for new projects. It is designed to be forked/cloned to create specialized AI agents or applications.
**Key Contact**: JMCJDOG (jared.cohen55@gmail.com)

## 2. Structural Logic
The filesystem is organized to separate concerns and facilitate template instantiation:

| Path | Purpose | Agent Action |
|------|---------|--------------|
| `src/` |  Source code (`src/app` package) | **Edit here** for application logic. |
| `tests/` | Pytest suite | **Add tests here** corresponding to new features. |
| `Projects/` | **Product Factory** | **Target location** for generating new distinct projects. |
| `Sandbox/` | Experimental Zone | Use for scratchpads or temp scripts. Ignored by git? Check .gitignore. |
| `Resources/` | Dependency mgmt | Edit `requirements.txt` (Python) or `package.json` (npm). |
| `.agent/workflows/` | **Autonomous capabilities** | **Read these** to understand available turbo actions. |
| `Makefile` | Command abstraction | Use `make` commands for standard reliable execution. |
| `docker-compose.yml` | Container Orchestration | Defines the standard dev/prod container stack. |
| `.github/workflows/` | CI/CD | GitHub Actions definitions. |

## 3. Autonomous Capabilities (Turbo Workflows)
The system is equipped with "Turbo Workflows" located in `.agent/workflows/` that allow for autonomous execution without constant user approval.

> **CRITICAL**: Always prefer these workflows over manual command construction.

### Core Workflows
*   **`/test`**: Auto-runs the full test suite with coverage.
*   **`/dev`**: Starts the local development server (FastAPI) or Docker stack.
*   **`/setup`**: Hydrates the environment (venv creation, dependency install).
*   **`/git-push`**: Auto-stages, commits, and pushes to `origin master`.
*   **`/docker`**: Build and run Docker containers.

### Planning & Verification Workflows
*   **`/plan`**: Create structured planning documents before implementation.
*   **`/verify`**: Post-implementation verification (tests, lint, plan compliance).
*   **`/debug`**: Systematic debugging with root cause analysis.
*   **`/progress`**: Quick project status check (git, tests, TODOs).

### Factory Workflow
*   **`/new-project`**: **The Factory**. Spawns NEW separate projects from this template into `Projects/`.

## 4. Operational Standards

### Development Cycle
1.  **Plan** with `/plan` (for non-trivial features).
2.  **Modify** code in `src/app`.
3.  **Verify** with `/verify` (runs tests + validation).
4.  **Deploy/Save** with `/git-push`.

### The Factory Pattern (Creating New Products)
To start a new product (e.g., `weather-bot`):
1.  **Do NOT** build it inside `src/`. `src/` is the *template's* source.
2.  **EXECUTE** the `/new-project` workflow.
3.  **TARGET** the `Projects/` directory (e.g., `Projects/weather-bot`) to keep the workspace organized.
4.  This creates a fresh git repo detached from the root history.

## 5. Technology Stack & Constraints
*   **Language**: Python 3.13+
*   **Backend**: FastAPI, LangGraph (agent orchestration)
*   **Frontend**: Next.js, Vercel AI SDK (see `Resources/package.json`)
*   **Standards**:
    *   **Docstrings**: REQUIRED for all modules and functions (Google style).
    *   **Type Hints**: REQUIRED for all function arguments and returns.
*   **Package Mgmt**: `pip` with `setup.cfg` (editable install `pip install -e .`).
*   **Testing**: `pytest`
*   **Container**: Docker (see `Dockerfile` & `docker-compose.yml`)
*   **Linting**: Flake8/Black (implied via CI)

## 6. Expert Tips for Agents
*   **Authentication**: The environment is pre-authenticated with GitHub via SSH (`C:\Users\jared\.ssh\id_ed25519`).
*   **Settings**: VS Code settings are in `AppData/.../User/settings.json`. Font size is managed there.
*   **Context Awareness**: If asked to "fix" something, ALWAYS run `/test` first to establish a baseline, then fix, then run `/test` again.
*   **Use Workflows**: Prefer `/plan` → `/verify` cycle for complex changes.
