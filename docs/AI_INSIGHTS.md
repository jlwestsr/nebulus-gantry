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
- **Thread Title Matching**: The frontend uses "New Thread" as the default title for new threads. This string must match the backend default in `chat_service.py` exactly for auto-title generation to work correctly.
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
- **Light/Dark Theme**: Implemented. `Settings.tsx` toggles `.dark` class on `<html>` via `document.documentElement.classList.toggle()`. Theme persists in `localStorage('nebulus-theme')`. Default is dark.
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

## 10. Session Notes (2026-02-06) — Brand Integration Phase 2

### Tailwind v4 Dark Mode with CSS Custom Properties

- **`@theme` resolves `var()` statically**: In Tailwind v4, `@theme { --color-n-bg: var(--n-bg); }` resolves `var(--n-bg)` at build time using `:root` values. The `.dark` class overrides never propagate. The entire app renders in light theme even when `.dark` is on `<html>`.
- **Fix: `@theme inline`**: Use `@theme inline { --color-n-bg: var(--n-bg); }` — the `inline` keyword keeps `var()` references dynamic at runtime so `.dark` class overrides work correctly.
- **CSS variable declarations outside `@layer base`**: Move `:root` and `.dark` blocks out of `@layer base` for proper specificity. `@layer base` has lower priority than unlayered rules.
- **`.dark` class must be applied**: The app defaults to dark theme but nothing was adding `class="dark"` to `<html>`. Fixed in three places: `index.html` (default), `main.tsx` (reads localStorage on load), `Settings.tsx` (toggles class on change via `document.documentElement.classList.toggle`).
- **`@custom-variant dark`**: Not needed if using `.dark` class directly in CSS selectors. Only needed if you want `dark:` utility variants to respond to the class instead of `prefers-color-scheme`.

### Brand Token Architecture (`nebulus.css`)

- **Token flow**: `:root`/`.dark` define `--n-*` raw values → `@theme inline` maps `--color-n-*: var(--n-*)` → Tailwind generates `bg-n-*`, `text-n-*`, `border-n-*` utilities.
- **File location**: `frontend/src/styles/nebulus.css`, imported via `@import "./styles/nebulus.css"` in `index.css`.
- **Dark theme calibrated values**: `--n-bg: #141416`, `--n-panel: #222226`, `--n-panel-2: #2A2A30`, `--n-border: #3C3C42`, `--n-muted: #969696`.

### SVG Glyph as `<img>` vs Inline `<svg>`

- **`currentColor` does not inherit via `<img>`**: When an SVG with `stroke="currentColor"` is loaded as `<img src="...">`, `currentColor` defaults to black — it cannot inherit the parent element's CSS color. The glyph renders as a black mark on dark backgrounds.
- **Fix: inline `<svg>`**: Inline SVGs inherit `currentColor` from the parent's `color` property (via `text-n-text` etc.). Always use inline SVGs when `currentColor` inheritance is needed.
- **Static SVG file kept for favicon**: `public/brand/nebulus-glyph.svg` is still used as the favicon (`<link rel="icon">`). Favicons don't need `currentColor` — browsers render them in their own context.

### Micro-Glyph Design at Icon Scale

- **Complex glyphs collapse at 16px**: The original containment-frame + chevron glyph (4 paths, partial box with X-like crossings) was visually identical to a browser broken-image icon at 16px. Design for the target size, not the design canvas.
- **Final glyph: Neural Spike**: `M24 72H48L62 36L78 92L90 52H108` — a single continuous waveform stroke. Flat baseline entry, asymmetric peak-trough-recovery, flat exit. StrokeWidth 10 at 16px, 8 at 24px.
- **Glyph selection criteria**: No closed geometry (avoids box/container confusion), no line crossings, no symmetry, open endpoints at different positions.

### Thread Terminology

- **"Conversation" → "Thread" everywhere in UI**: All user-facing copy uses "thread(s)". Internal code (variable names, API routes, database models) still uses "conversation" — only the display strings changed.
- **Backend default title**: `chat_service.py` uses `"New Thread"` as the default title. Frontend checks `data.conversation.title !== 'New Thread'` for auto-title detection. These strings must match exactly.
- **Conversation title in AI_INSIGHTS.md Section 2**: The pitfall note about "Conversation Title Matching" still references the old string. The actual default is now `"New Thread"`.

## 11. Session Notes (2026-02-09) — Platform-Agnostic Refactoring (v2.2.0)

### Platform Bridge Architecture (`backend/platform.py`)

- **Single source of truth**: `get_llm_base_url()`, `get_chroma_settings()`, and `get_default_model()` replace the old `Settings.tabby_host` and `Settings.chroma_host` fields.
- **Cascading priority**: Environment variables → nebulus-core `PlatformAdapter` → hardcoded defaults. This means Docker env vars (e.g., `TABBY_HOST`, `CHROMA_HOST`) still work identically, but bare-metal deployments can rely on the adapter.
- **Lazy adapter loading**: `_load_adapter()` is called once on first use and cached. If nebulus-core is unavailable (import fails, no adapter registered), it silently falls back — never crashes.
- **Import path**: `from backend.platform import get_llm_base_url, get_chroma_settings, get_default_model`

### Config.py Slimmed

- `backend/config.py` now only contains Gantry-local settings: `database_url`, `secret_key`, `session_expire_hours`. Service endpoint configuration moved to `platform.py`.
- Other consumers of `Settings` (`auth_service.py`, `dependencies.py`) are unaffected — they only use the remaining fields.

### ChromaDB Dual-Mode Support

- `chroma_pool.py` now attempts nebulus-core's `VectorClient` first, which handles both HTTP mode (Prime/Docker) and embedded mode (Edge/bare-metal) automatically.
- Falls back to direct `chromadb.HttpClient` or `chromadb.PersistentClient` if nebulus-core is unavailable.
- `get_chroma_client()` return type widened from `chromadb.HttpClient` to `chromadb.ClientAPI` — all consumers (`memory_service.py`, `document_service.py`) use the `ClientAPI` interface and are unaffected.
- New `get_vector_client()` function exposes the higher-level `VectorClient` for future code.

### nebulus-core in Docker

- Volume mount: `../nebulus-core/src:/core:ro` (read-only).
- `PYTHONPATH=/app:/atom:/core` — allows `from nebulus_core.platform import ...` inside the container.
- No pip install needed — volume mount + PYTHONPATH is simpler and avoids build-step complexity.

### Key Constraint: Async Streaming Preserved

- nebulus-core's `LLMClient` is **sync-only** with no streaming support. Gantry's async `httpx.AsyncClient` SSE streaming in `llm_service.py` must be preserved.
- The integration is a **configuration bridge only** — source URLs from the adapter, keep Gantry's async implementation. Do not attempt to replace `LLMService` with `LLMClient`.

### Known Issue: ProposalStore.list_all

- **Pre-existing bug**: `GET /api/overlord/audit/proposals` throws `AttributeError: 'ProposalStore' object has no attribute 'list_all'` in `overlord_service.py:227`. The `list_proposals()` method calls `self._proposal_store.list_all()` but the upstream `ProposalStore` in nebulus-atom doesn't expose that method. This predates the platform bridge work and needs an upstream fix in nebulus-atom.

### Release

- Tagged `v2.2.0` on `main`. Previous release was `v2.1.0`.

## 12. Session Notes (2026-02-10) — Track 6: Gantry-Overlord Unification

### Track 6 Overview

Track 6 unifies Gantry's chat interface with the Overlord meta-orchestrator. The user talks to one AI; Overlord routes to the right backend (Claude, Gemini, Local LLM, or the dispatch engine). Design doc: `docs/plans/2026-02-10-gantry-overlord-unification.md`.

### Phase A: Backend Plumbing — Complete

- **Dispatch Protocol**: `DispatchRequest` → SSE stream of `DispatchEvent` objects (`thinking`, `content`, `action`, `result`, `status`, `approval_request`, `error`). Schema in `backend/schemas/dispatch.py`.
- **Conversation Router** (`backend/services/conversation_router.py`): Pattern-based intent classification (halt > status > dispatch > question). Worker selection heuristics: code keywords → Claude, strategy keywords → Gemini, default → Local LLM.
- **SSE Endpoint**: `POST /api/chat/dispatch` streams `DispatchEvent` objects. Frontend consumes via `dispatchApi.sendMessage()` async generator using `ReadableStream` reader.
- **Dispatch Bridge** (`dispatch_from_chat()` in `overlord_service.py`): Bridges Gantry chat to the real Dispatcher (Analyze → Brief → Provision → Execute → Review). Creates WorkQueue task, runs governance, builds workers dict, calls `Dispatcher.dispatch_task()`. Falls back to `execute_task()` if Dispatcher modules unavailable.
- **Governance Enforcement**: `run_governance_check()` in OverlordService runs pre-dispatch checks via `GovernanceEngine.pre_dispatch_check()`. Both the ConversationRouter and `dispatch_from_chat()` enforce governance.
- **Test Count**: 398 tests after Phase A (49 new: 7 dispatch bridge, 16 conversation router, 26 existing overlord router).

### Phase A: GAP Fixes

- **GAP-1 (Wrong Dispatch Engine)**: `_handle_dispatch()` in ConversationRouter originally called `execute_task()` (Phase 2 DispatchEngine) instead of the real Dispatcher. Fixed by calling `dispatch_from_chat()` which routes through the full Dispatcher lifecycle.
- **GAP-2 (Governance Bypass)**: ConversationRouter's dispatch path had no governance check. Fixed by adding `svc.run_governance_check()` before `svc.dispatch_from_chat()`.
- **Test Isolation for nebulus_swarm**: Since `nebulus_swarm` isn't installed in Gantry's venv, tests use `sys.modules` injection via an `inject_modules` pytest fixture. Mock `ModuleType` objects are created for the entire `nebulus_swarm.overlord.*` hierarchy. Setting `sys.modules[key] = None` blocks imports even in environments where the package is installed (e.g., pre-commit venv at `/home/jlwestsr/.python3_venv`).

### Phase B: Situation Map UI — Complete

- **SituationMap.tsx** (`frontend/src/components/SituationMap.tsx`): Collapsible right-side panel with three sections:
  - Active Agents: Polls `GET /api/overlord/dispatch/active` every 5s. Worker badges: Claude = purple/violet, Gemini = blue, Local = emerald. Status badges with color-coded backgrounds.
  - Daily Budget: Token bar with color thresholds (green <60%, yellow 60-80%, red >80%). Shows tokens used/ceiling and cost used/ceiling.
  - Halt Button: Red button at bottom with confirmation dialog. Calls `POST /api/overlord/halt`. Shows result toast for 5 seconds.
  - Mobile: Uses `max-md:absolute` positioning for overlay on small screens.
- **NotificationBlock.tsx** (`frontend/src/components/NotificationBlock.tsx`): Renders 5 event types inline in chat:
  - `thinking`: Collapsed gray block with expand toggle and pulse indicator
  - `status`: Blue-gray info block with info icon
  - `result`: Card with worker/tokens/status metadata badges
  - `approval_request`: Yellow block with Approve/Deny buttons that call `overlordApi.approveProposal()`/`denyProposal()`
  - `error`: Red alert block with error icon
- **dispatchStore.ts** (`frontend/src/stores/dispatchStore.ts`): Zustand store managing `activeDispatches`, `budget`, `events`, `sidebarOpen`. Sidebar state persists in `localStorage('gantry-situation-map-open')`. Actions: `fetchActiveDispatches`, `fetchBudget`, `addEvent`, `clearEvents`, `toggleSidebar`, `haltAll`.
- **Chat.tsx Integration**: Imports SituationMap and NotificationBlock. Non-content events routed to `dispatchStore.addEvent()`. Events cleared on conversation change and before each new message. Sidebar toggle button in chat header (double chevron icon). Notification blocks rendered between header and message list.
- **Backend Endpoints (3 new)**:
  - `GET /api/overlord/budget` → `BudgetResponse` (tokens_used_today, token_ceiling, cost_usd_today, cost_ceiling_usd, usage_pct)
  - `GET /api/overlord/dispatch/active` → `ActiveDispatchListResponse` (list of dispatch cards)
  - `POST /api/overlord/halt` → halt result (message, tasks_cancelled, daemon_stopped)
  - All require admin auth via `Depends(require_admin)` + `Depends(_get_service)` with 503 graceful degradation.
- **OverlordService.get_budget_status()**: Queries `WorkQueue.get_daily_usage()` for token/cost data. Returns zeros when WorkQueue is unavailable.
- **Test Count**: 407 tests after Phase B (10 new: 4 budget, 3 active dispatches, 3 halt).

### Phase C: Provider Management UI — BACKLOG

Not scheduled. See design doc Section 5 for details. Adds pluggable LLM provider management with encrypted API keys, role assignment, fallback chains, and hot-reload.

### Phase D: Full Plant Manager Mode — BACKLOG

Not scheduled. Intent-driven task intake, plan decomposition, multi-agent execution with live progress, intervention controls (redirect, pause, kill, inspect).

### Patterns Established

- **Dispatch Event Consumption**: `for await (const event of dispatchApi.sendMessage({...}))` with type-based routing: `content` → message update, `error` → error state + dispatch store, everything else → dispatch store for sidebar + inline rendering.
- **Sidebar Polling Pattern**: `useEffect` with `setInterval(5000)` for active dispatches and budget. Cleanup on unmount via returned function.
- **Confirmation Dialog Pattern**: `showHaltConfirm` state toggles between single button and confirm/cancel pair. No external dialog library — inline Tailwind-styled buttons.
- **Admin-Only Situation Map Endpoints**: Follow same `Depends(require_admin) + Depends(_get_service)` pattern as all other overlord endpoints. Service method returns dict, router wraps in Pydantic response model.

## 13. Session Notes (2026-02-10) — Edge Deployment & LLM Connectivity Fixes

### Port Reassignment

- **Open WebUI moved from port 3000 → 3001** (`nebulus-edge/body/docker-compose.yml`). Gantry frontend now owns port 3000.
- **Gantry frontend moved from port 3001 → 3000** (`docker-compose.yml`). When running bare-metal (not Docker), start with `npm run dev -- --host 0.0.0.0 --port 3000`.
- **Port mapping summary (Mac Mini)**: Gantry frontend = 3000, Open WebUI = 3001, Gantry backend = 8000, Brain (MLX) = 8080, Intelligence = 8081.

### macOS Firewall

- **Application Firewall blocks unlisted binaries**: The macOS Application Firewall (`socketfilterfw`) must explicitly allow each binary that listens on a network port. Homebrew Python (`/opt/homebrew/Cellar/python@3.12/.../Python.app`) and Node.js (`/opt/homebrew/Cellar/node/25.4.0/bin/node`) both needed to be added manually via `sudo socketfilterfw --add` + `--unblockapp`.
- **Docker.app is pre-allowed**: Docker containers (Open WebUI) are reachable by default.

### CORS Configuration

- **LAN IP required in CORS origins**: When accessing Gantry from a remote dev machine, the browser sends `Origin: http://192.168.4.30:3000`. This must be in `allow_origins` or the backend rejects preflight requests with `400 Disallowed CORS origin`.
- **Current approach**: Origins list opened to `["*"]` for lab/dev access (commit `7a784ed` from dev machine).
- **Cookie SameSite**: Session cookies use `samesite="lax"`. This works for same-site cross-port requests (e.g., `192.168.4.30:3000` → `192.168.4.30:8000`) but NOT for cross-site (e.g., `localhost:3000` → `192.168.4.30:8000`).

### Frontend API URL

- **`VITE_API_URL` env var**: Frontend uses `import.meta.env.VITE_API_URL || 'http://localhost:8000'` for all API calls. When serving to remote clients, this must point to the Mac Mini's LAN IP. Set via `frontend/.env` (gitignored): `VITE_API_URL=http://192.168.4.30:8000`.
- **Vite restart required**: `.env` changes require a Vite restart — they are not hot-reloaded.

### LLM Base URL Double-Path Bug

- **Root cause**: Edge adapter's `llm_base_url` returns `http://localhost:8080/v1` (with `/v1` suffix, per nebulus-core convention). Gantry services (`llm_service.py`, `conversation_router.py`, `model_service.py`) append `/v1/...` themselves, resulting in `http://localhost:8080/v1/v1/models` (404).
- **Fix**: `get_llm_base_url()` in `backend/platform.py` now strips `/v1` suffix from whatever the adapter returns via `.removesuffix("/v1")`. This keeps the core adapter convention intact while preventing Gantry from doubling the path.

### Model Name Mismatch

- **Root cause**: Edge adapter's `default_model` was `mlx-community/Meta-Llama-3.1-8B-Instruct` but the brain serves `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit`. The brain returns 404 for unknown model names (tries to fetch from HuggingFace).
- **Fix (edge)**: Updated `EdgeAdapter.default_model` to `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit`.
- **Fix (gantry)**: `conversation_router.py` and `llm_service.py` now use `get_default_model()` instead of hardcoded `"default"` string.

### Overlord Conditional UI

- **Problem**: Overlord nav link showed even when `nebulus_swarm` isn't installed. The check hit `/api/overlord/dashboard` which requires auth — returning 401, not 503, so the UI thought Overlord was available.
- **Fix**: Added unauthenticated `GET /api/overlord/available` endpoint that returns `{"available": true/false}`. Frontend `uiStore.checkOverlord()` calls this via the proper `VITE_API_URL` base.

### Bare-Metal Backend on Mac Mini

- **Process supervisor**: Uvicorn runs as a bare-metal process (not Docker, not PM2) with auto-restart. Killing the process spawns a new one automatically. PID changes on restart.
- **Log locations**: Access log at `/private/var/log/nebulus/gantry-backend.log`, error log at `/private/var/log/nebulus/gantry-backend-error.log`.
- **`__pycache__` stale bytecode**: After editing Python files, the auto-restarted process may load cached `.pyc` files. Clear with `find backend -name __pycache__ -exec rm -rf {} +` before restart for reliable code updates.

### Git Remote URLs

- **HTTPS → SSH**: Both `nebulus-edge` and `nebulus-gantry` remotes were switched from HTTPS to SSH (`git@github.com:jlwestsr/...`) because the Mac Mini doesn't have HTTPS credentials configured. The remote URL can revert to HTTPS after `set-url`, so verify with `git remote -v` before pushing.

## 14. Session Notes (2026-02-11) — Architect Review #7 + MVA Hardening

### Merged Branches

| Branch | Scope | Tests |
|--------|-------|-------|
| `fix/rate-limiter-architect-review` | Rate limiter moved from `backend/middleware/` → `backend/utils/`, keyed by email (not IP) for NAT-friendly LAN, escalation capped at `min(count, 4)` (~4h max lockout) | 14 |
| `fix/cors-tighten-spec` | CORS tightened per `mva-cors-config` spec: removed PATCH from methods, trimmed headers to `Content-Type` + `Authorization`, hardcoded `secure=False` for HTTP-only LAN | 5 |

### Persona Seed Infrastructure

- **Fixture created**: `backend/fixtures/personas/dealership_analyst.json` — Dealership Analyst persona with `is_default: true`, `temperature: 0.4`, automotive retail system prompt.
- **Test file created**: `backend/tests/test_seed_personas.py` — 5 tests (create, idempotency, empty dir, malformed JSON, missing name). Uses in-memory SQLite with `StaticPool` per project patterns.
- **Original sub-agent files were non-functional**: The Moto sub-agents created initial versions of the fixture and test file, but the tests lacked the `DATABASE_URL` env override and `StaticPool` needed for in-memory SQLite. Both files were rewritten.
- **Seed script**: `backend/scripts/seed_personas.py` accepts optional `db` session and `fixtures_dir` for testability. Idempotent — checks for existing system persona by name before inserting.

### Docker Bind-Mount File Ownership

- **Recurring pitfall**: Docker Compose bind-mounts create files as `root:root` inside the container. On the host, `backend/data/` and `data/` directories end up root-owned, causing `sqlite3.OperationalError: attempt to write a readonly database`.
- **Actual DB path**: `data/gantry.db` (relative to project root), NOT `backend/data/nebulus.db`. The `DATABASE_URL` setting is `sqlite:///./data/gantry.db`.
- **Fix**: `sudo chown -R jlwestsr:jlwestsr data/` after any Docker rebuild that recreates the volume. SQLite requires write access to both the `.db` file AND its parent directory (for WAL/journal files).
- **`backend/data/nebulus.db`**: This is an empty 0-byte file left over from an earlier Docker config. The real database is `data/gantry.db`.

### Test Suite Status

- **549 tests passing** (48s). Zero failures. 126 warnings (all Starlette cookie deprecation — harmless).

## 15. Session Notes (2026-02-19) — Reboot Recovery & Infrastructure Hardening

### Gantry Down After System Reboot

- **Root cause**: Gantry's `docker-compose.yml` had no `restart` policy on either service. After a system reboot, the Prime stack (`restart: unless-stopped`) came back automatically but Gantry's backend and frontend stayed down (exited 2 days prior).
- **Fix**: Added `restart: unless-stopped` to both `backend` and `frontend` services in `docker-compose.yml`. Gantry will now survive reboots like the Prime stack.
- **Rebuilt and verified**: `docker compose up -d --build` — both containers healthy, backend at `:8000` (200), frontend at `:3001` (200).

### Open WebUI Decommissioned

- **Action**: Open WebUI container stopped and restart policy changed to `restart: "no"` in `nebulus-prime/docker-compose.yml`. Gantry is now the primary chat UI — Open WebUI is retained in the compose file but will not auto-start.
- **Port 3000 freed**: Open WebUI was on `127.0.0.1:3000`. This port is now available if Gantry frontend needs to move from 3001 → 3000 in a future cleanup.

### Infrastructure Checklist

- All Docker services that should survive reboots must have `restart: unless-stopped`
- Prime services (tabby, dozzle, chromadb, mcp-server): already had restart policy ✅
- Gantry services (backend, frontend): added restart policy ✅
- Open WebUI: explicitly disabled ✅
