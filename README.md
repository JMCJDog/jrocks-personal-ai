# Vibe Coding

![CI](https://github.com/JMCJDOG/vibe-coding/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A starter local/edge AI project scaffolded for development and deployment.

## Repository Layout

| Path | Description |
|------|-------------|
| `src/` | Application package (`app`) |
| `Resources/` | Dependency lists and constraints |
| `tests/` | Pytest tests |
| `.github/workflows/` | CI and publish workflows |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root endpoint with welcome message |
| GET | `/health` | Health check for monitoring |
| GET | `/docs` | Interactive Swagger UI (auto-generated) |
| GET | `/redoc` | ReDoc API documentation |

## Quickstart (Local)

1. **Create and activate virtual environment:**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies (editable install):**

   ```powershell
   make install
   ```

3. **Run the app in dev mode:**

   ```powershell
   make run
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs

## Testing

```powershell
make test
```

See [TESTING.md](TESTING.md) for detailed testing workflow.

## Docker (Production)

```powershell
make docker-build
make docker-run
```

## CI/CD

GitHub Actions runs tests and builds images on every push. See:
- `.github/workflows/ci.yml` - Test and build
- `.github/workflows/publish.yml` - Push images to GHCR

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT - See [LICENSE](LICENSE) for details.
