# Project AI Insights (Long-Term Memory)

## Purpose

This document serves as the **long-term memory** for AI agents working on **Nebulus Gantry**. It captures project-specific behavioral nuances, recurring pitfalls, and architectural decisions that are not strictly rules (those live in `AI_DIRECTIVES.md`) but are critical for maintaining continuity across sessions.

## 1. Architectural Patterns

- **Zustand Store Pattern**: All client state lives in Zustand stores (`authStore`, `chatStore`, `toastStore`, `uiStore`). No prop drilling. Components subscribe to store slices directly.
- **SSE Streaming (Two Patterns)**: The project uses two SSE patterns depending on the use case:
  - **Chat messages**: `ReadableStream` reader with manual chunk decoding (requires POST body for the user message).
  - **Admin log streaming**: `EventSource` with `withCredentials: true` (read-only GET, handles auto-reconnect). Use `EventSource` for persistent read-only streams and `ReadableStream` when the request requires a body.
- **Graceful Degradation**: ChromaDB, NetworkX, Docker, and TabbyAPI failures are caught and logged — the app continues operating without those features. Never let a missing external service crash the application.
- **Session-Based Auth**: Authentication uses httponly cookies with bcrypt-hashed passwords. The `get_current_user` dependency validates on every request. Admin access uses the `require_admin` dependency.
- **LTM Injection**: On each message, the backend queries ChromaDB for similar past messages and NetworkX for related entity facts, then prepends them to the system prompt.

## 2. Recurring Pitfalls

- **passlib/bcrypt Incompatibility**: Do not use `passlib` for password hashing. Use the `bcrypt` library directly. passlib has known compatibility issues with recent bcrypt versions.
- **host.docker.internal on Linux**: `host.docker.internal` does not work reliably on Linux. Use container hostnames on the `nebulus_ai-network` Docker network instead (e.g., `chromadb`, `tabby`).
- **CORS Origins**: The backend CORS configuration must include all development ports. Missing a port (e.g., `3001` for the frontend Docker container) will cause silent request failures.
- **Tailwind CSS v4**: Tailwind v4 uses `@plugin` syntax, not `@import`. Do not use Tailwind v3 patterns.
- **Conversation Title Matching**: The frontend uses "New Conversation" as the default title for new conversations. This string must match the backend default exactly for auto-title generation to work correctly.
- **PYTHONPATH for Tests**: Pre-commit hooks run `pytest` with `PYTHONPATH` set to include `src/` and the project root. If tests fail in pre-commit but pass locally, check the `PYTHONPATH` configuration in `.pre-commit-config.yaml`.
- **Docker `follow=True` Hangs Tests**: The `DockerService.stream_logs()` method uses `follow=True` which creates an infinite stream. Tests that hit the SSE log endpoint **must** mock `_docker_service` — otherwise the test client will hang indefinitely waiting for the stream to end.
- **Test File E402 Imports**: Several test files use `os.environ.setdefault("DATABASE_URL", ...)` before imports, triggering flake8 E402. These are suppressed with `# noqa: E402` and are necessary — the env var must be set before any backend module is imported.
- **package-lock.json Drift**: When adding frontend dependencies, always commit `package-lock.json` in the same commit. The markdown rendering feature (`react-markdown`, `rehype-highlight`, `remark-gfm`, `@tailwindcss/typography`) was committed without its lock file update — this was caught and fixed later.

## 3. Workflow Nuances

- **Pre-Commit Hooks Run pytest**: Every Python file change triggers a full test run via pre-commit. The `PYTHONPATH` must be correctly set in `.pre-commit-config.yaml`.
- **Docker Volumes for Hot-Reload**: Docker Compose mounts `./backend` and `./frontend` as volumes for live code reloading during development. Backend uses uvicorn `--reload`, frontend uses Vite HMR.
- **`bin/gantry validate`**: Runs `pre-commit run --all-files`. This is the canonical way to verify all linting and tests pass before committing.
- **Pre-existing Lint Failures**: `bin/gantry validate` has pre-existing failures in `djlint` (missing meta tags in `index.html`) and `flake8` (unused imports in `conftest.py`, `test_model_service.py`, `test_graph_service.py`). These are not blockers — focus on ensuring `pytest` passes and your own files are clean.
- **Feature Specs Archival**: The `docs/features/` directory contained specs from the v1 Chainlit codebase referencing `src/nebulus_gantry/`. These have been archived to `docs/features/archive/`. New feature specs should reference the v2 structure (`backend/`, `frontend/src/`).

## 4. Infrastructure Notes

- **External Docker Network**: `nebulus_ai-network` is an external Docker network shared with TabbyAPI and ChromaDB containers managed by Nebulus Prime. Gantry joins this network to communicate with those services.
- **Port Mappings**:
  - Backend: `8000:8000`
  - Frontend: `3001:3000` (host 3001 → container 3000)
  - TabbyAPI: `5000` (on `nebulus_ai-network`)
  - ChromaDB: `8001` (on `nebulus_ai-network`, mapped as port 8000 inside the container)
- **ChromaDB Host**: In `docker-compose.yml`, `CHROMA_HOST` is set to `http://chromadb:8000` (the container's internal port), not `http://localhost:8001`.

## 5. Implementation Completeness (v2)

- **Admin Log Streaming**: Fully implemented. `DockerService.stream_logs()` → SSE endpoint → `LogsTab` with live viewer, auto-scroll, pause/clear, connection status. Uses `EventSource` with cookie auth.
- **Light Theme**: Not implemented. `Settings.tsx` shows "not yet available" message. Dark mode only.
- **v2 Maturity**: ~98% complete. All core features (auth, chat, LTM, admin services/models/users/logs, settings) are production-ready with tests.
