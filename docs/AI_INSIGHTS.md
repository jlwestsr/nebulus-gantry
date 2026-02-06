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
- **Tailwind CSS v4 Import Syntax**: The CSS entry point MUST use `@import "tailwindcss"` (bare specifier), NOT `@import url("tailwindcss")`. The `url()` wrapper prevents the `@tailwindcss/vite` plugin's content scanner from connecting to the module graph, resulting in theme/base loading but zero utility classes generated. The `stylelint` `import-notation` rule is disabled in `.stylelintrc.json` to prevent auto-fixing back to `url()` syntax.
- **Tailwind CSS v4 Syntax**: Tailwind v4 uses `@plugin` syntax, not `@import` for plugins. Do not use Tailwind v3 patterns.
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

## 5. Knowledge Vault & RAG Patterns (Tier 1.5)

- **Document Service Architecture**: `DocumentService` handles upload, text extraction, chunking, and ChromaDB indexing. Text extractors: `pypdf` for PDF, `python-docx` for DOCX, direct read for TXT/CSV.
- **Chunking Strategy**: 2000-character chunks with 100-character overlap. Metadata includes `document_id`, `chunk_index`, `filename` for citation reconstruction.
- **ChromaDB Collection Naming**: User documents use `user_{user_id}_documents` collection pattern (mirrors LTM pattern `user_{user_id}_ltm`).
- **RAG Context Injection**: `build_rag_context()` in `chat.py` queries ChromaDB for top-k similar chunks, formats them with `[Source: filename]` headers, and prepends to system prompt alongside LTM context.
- **Document Scope**: Conversations can optionally scope RAG to specific documents/collections via `document_scope` JSON field. If empty, RAG searches all user documents.
- **Frontend Integration**: `KnowledgeVault.tsx` is a collapsible sidebar section. Uses `documentStore` for state. Upload triggers immediate indexing (status: processing → ready/failed).

## 6. Personas Patterns (Tier 1.5)

- **Persona Types**: User personas (`user_id` set) are private. System personas (`user_id = NULL`) are admin-created and visible to all users.
- **Conversation Assignment**: `persona_id` FK on conversations. When set, the persona's `system_prompt` replaces the default system prompt in `stream_message()`.
- **Temperature Override**: Personas can specify `temperature` (0.0-2.0). `LLMService.stream_chat()` accepts optional `temperature` parameter that overrides the model default.
- **Access Control Pattern**: `PersonaService` methods check `user_id` ownership for user personas. System personas (user_id=NULL) are read-only except via admin endpoints.
- **Frontend Flow**: `PersonaSelector.tsx` dropdown in chat header → fetches personas on mount → calls `PATCH /api/chat/conversations/{id}/persona` on change.

## 7. Implementation Completeness (v2)

- **Admin Log Streaming**: Fully implemented. `DockerService.stream_logs()` → SSE endpoint → `LogsTab` with live viewer, auto-scroll, pause/clear, connection status. Uses `EventSource` with cookie auth.
- **Knowledge Vault (Tier 1.5)**: Fully implemented. Document upload (PDF/TXT/CSV/DOCX), ChromaDB indexing, RAG retrieval with citations, collection management. 22 tests.
- **Personas (Tier 1.5)**: Fully implemented. User and system personas, temperature control, conversation assignment, admin management. 26 tests.
- **Light Theme**: Not implemented. `Settings.tsx` shows "not yet available" message. Dark mode only.
- **v2 Maturity**: Tier 1 complete (1.1-1.5). 272 backend tests passing. Ready for Tier 2 (compliance features).

## 8. Session Notes (2026-02-05)

- **Tier 1.5 Released**: Knowledge Vault + Personas shipped as `v0.1.5`. Branch `feat/knowledge-vault-personas` merged to `develop` then `main`.
- **Flake8 Patterns**: Test files with `os.environ.setdefault()` before imports need `# noqa: E402` on all subsequent imports. Use `# noqa: E402, F401` when the import is also only for side effects (model registration).
- **F-string Without Placeholders**: Flake8 F541 catches `f"static string"` — remove the `f` prefix if no interpolation is needed.
- **Unused Import Cleanup**: When removing unused schema imports from routers, verify they're not used in endpoint signatures before deleting.
- **Combined Commits**: When features are tightly coupled (shared files like `api.ts`, `types/api.ts`), a single combined commit is cleaner than trying to split artificially.

## 9. Session Notes (2026-02-06) — Tier 1.5 Manual Testing

### Database Initialization

- **New tables require restart or manual creation**: After adding new models (Persona, Collection, Document), the tables may not exist if the container was running during code deployment. Run `Base.metadata.create_all(bind=engine)` inside the container or restart to trigger table creation.
- **Database location**: Production database is at `/app/data/gantry.db` (inside container), configured via `DATABASE_URL=sqlite:///./data/gantry.db`.
- **Schema uses `role` not `is_admin`**: The User model uses a `role` column (`admin`/`user`) rather than a boolean `is_admin`.

### Personas Feature — Verified Working

| Test | Status |
|------|--------|
| Create user persona | ✅ |
| List personas (user + system) | ✅ |
| Assign persona to conversation | ✅ |
| Chat uses persona's system_prompt | ✅ |
| Temperature override (tested 0.3) | ✅ |
| Admin create system persona | ✅ |
| System personas visible to all users | ✅ |

**API Endpoints Tested:**

- `POST /api/personas` — Create user persona
- `GET /api/personas` — List all (user + system)
- `PATCH /api/chat/conversations/{id}/persona` — Assign persona
- `POST /api/admin/personas` — Create system persona

### Knowledge Vault Feature — Verified Working

| Test | Status |
|------|--------|
| Create collection | ✅ |
| Upload TXT document | ✅ |
| Document chunking & ChromaDB indexing | ✅ |
| List documents (with collection filter) | ✅ |
| Semantic search across documents | ✅ |
| Set document scope on conversation | ✅ |
| RAG retrieval injects context into chat | ✅ |
| Delete document (removes from DB + ChromaDB) | ✅ |
| Update collection metadata | ✅ |

**API Endpoints Tested:**

- `POST /api/documents/collections` — Create collection
- `POST /api/documents/upload` — Upload document (multipart/form-data)
- `GET /api/documents?collection_id=` — List documents
- `POST /api/documents/search` — Semantic search
- `PATCH /api/chat/conversations/{id}/document-scope` — Set RAG scope
- `DELETE /api/documents/{id}` — Delete document
- `PATCH /api/documents/collections/{id}` — Update collection

**Document Scope Format:**

```json
{"document_scope": [{"type": "collection", "id": 1}]}
{"document_scope": [{"type": "document", "id": 1}, {"type": "document", "id": 2}]}
```

### RAG Verification

- Uploaded two test documents (`test-doc.txt`, `api-guide.txt`)
- Semantic search correctly ranked `api-guide.txt` higher for authentication queries
- Chat with document scope correctly retrieved:
  - Supported formats (PDF, TXT, CSV, DOCX) and 10MB limit
  - Key components (React 19, FastAPI, TabbyAPI, ChromaDB)
- Responses grounded in document content, not hallucinated

### TabbyAPI Notes

- Model must be loaded before chat works: `POST /v1/model/load {"model_name": "..."}`
- 503 errors indicate no model loaded, not service down
- Model loading streams progress: `{"module": N, "modules": 67, "status": "processing"}`
