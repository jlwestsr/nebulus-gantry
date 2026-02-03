# Project AI Insights (Long-Term Memory)

## Purpose

This document serves as the **long-term memory** for AI agents working on **Nebulus Gantry**. It captures project-specific behavioral nuances, recurring pitfalls, and architectural decisions that are not strictly rules (those live in `AI_DIRECTIVES.md`) but are critical for maintaining continuity across sessions.

## 1. Architectural Patterns

- **Zustand Store Pattern**: All client state lives in Zustand stores (`authStore`, `chatStore`, `toastStore`, `uiStore`). No prop drilling. Components subscribe to store slices directly.
- **SSE Streaming**: Chat responses use Server-Sent Events (`StreamingResponse` with `text/event-stream`). The frontend reads the stream incrementally via `ReadableStream`.
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

## 3. Workflow Nuances

- **Pre-Commit Hooks Run pytest**: Every Python file change triggers a full test run via pre-commit. The `PYTHONPATH` must be correctly set in `.pre-commit-config.yaml`.
- **Docker Volumes for Hot-Reload**: Docker Compose mounts `./backend` and `./frontend` as volumes for live code reloading during development. Backend uses uvicorn `--reload`, frontend uses Vite HMR.
- **`bin/gantry validate`**: Runs `pre-commit run --all-files`. This is the canonical way to verify all linting and tests pass before committing.

## 4. Infrastructure Notes

- **External Docker Network**: `nebulus_ai-network` is an external Docker network shared with TabbyAPI and ChromaDB containers managed by Nebulus Prime. Gantry joins this network to communicate with those services.
- **Port Mappings**:
  - Backend: `8000:8000`
  - Frontend: `3001:3000` (host 3001 → container 3000)
  - TabbyAPI: `5000` (on `nebulus_ai-network`)
  - ChromaDB: `8001` (on `nebulus_ai-network`, mapped as port 8000 inside the container)
- **ChromaDB Host**: In `docker-compose.yml`, `CHROMA_HOST` is set to `http://chromadb:8000` (the container's internal port), not `http://localhost:8001`.
