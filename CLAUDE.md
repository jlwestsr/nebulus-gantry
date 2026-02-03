# CLAUDE.md — Project Context for Claude Code

## Project Overview

**Nebulus Gantry** is the full-stack AI chat interface for the Nebulus Prime ecosystem. It provides a dark-themed, Claude-like conversational UI with streaming LLM responses, long-term memory, multi-user authentication, and an admin control plane for managing services, models, and users.

Version 2 is a complete rewrite. The previous Chainlit/vanilla-JS codebase has been replaced with a modern React + FastAPI stack.

## Technical Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite 7, Tailwind CSS v4, Zustand |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2, SQLite, bcrypt |
| LLM | TabbyAPI (OpenAI-compatible endpoint) |
| Memory | ChromaDB (vector search), NetworkX (entity knowledge graph) |
| Auth | Session cookies (httponly, bcrypt-hashed passwords), admin/user roles |
| Deployment | Docker Compose, external `nebulus_ai-network` |

## Architecture

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │────▶│   TabbyAPI      │
│  React 19       │     │  FastAPI        │     │  LLM Inference  │
│  Port 3001→3000 │     │  Port 8000      │     │  Port 5000      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │   ChromaDB      │
                        │  Vector Store   │
                        │  Port 8001      │
                        └─────────────────┘
```

All services communicate over the external Docker network `nebulus_ai-network`.

## Critical Directives

1. **Docker-First Development**: The canonical way to run Gantry is via Docker Compose. All services must work within the container network.
2. **Git Workflow**: Feature branches off `main`. Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`). Never commit directly to `main`.
3. **Testing Requirements**: `pytest` for all backend changes. Pre-commit hooks enforce linting. Run `bin/gantry validate` before declaring work complete.
4. **Discovery-Driven Development**: Check existing architecture before proposing changes. Reference `CONTEXT.md` for patterns.

## Project Commands

```bash
# Docker operations
bin/gantry start        # docker compose up --build
bin/gantry stop         # docker compose down
bin/gantry rebuild      # docker compose up -d --build
bin/gantry restart      # docker compose restart
bin/gantry logs         # docker compose logs -f
bin/gantry status       # docker compose ps

# Testing & validation
bin/gantry test         # Run pytest via local venv
bin/gantry validate     # Run pre-commit hooks on all files

# Direct docker compose
docker compose up --build
docker compose exec backend pytest backend/tests/ -v
```

## Key Files & Directories

| Path | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app entry point, CORS, router registration |
| `backend/config.py` | `Settings` dataclass loaded from env vars |
| `backend/database.py` | SQLAlchemy engine and session factory |
| `backend/models/` | ORM models: `User`, `Conversation`, `Message`, `Session` |
| `backend/schemas/` | Pydantic request/response schemas |
| `backend/services/` | Business logic: Auth, Chat, LLM, Memory, Graph, Docker, Model |
| `backend/routers/` | API routes: `auth.py`, `chat.py`, `admin.py` |
| `frontend/src/stores/` | Zustand stores: auth, chat, toast, UI |
| `frontend/src/services/api.ts` | HTTP client wrapping `fetch` |
| `frontend/src/pages/` | Route-level page components |
| `frontend/src/components/` | Reusable UI components |
| `frontend/src/types/api.ts` | Shared TypeScript interfaces |
| `docker-compose.yml` | Service definitions and network config |
| `bin/gantry` | CLI entrypoint for common operations |
| `CONTEXT.md` | Full architectural context document |
| `AI_DIRECTIVES.md` | Strict operational rules for AI agents |
| `WORKFLOW.md` | Development workflow and SOPs |
| `docs/AI_INSIGHTS.md` | Long-term memory for AI agents |
| `docs/features/` | Feature specifications |

## Workflow for Features

1. **Discovery**: Read `docs/AI_INSIGHTS.md`, check existing code in `backend/` and `frontend/src/`
2. **Proposal**: Create implementation plan and feature spec in `docs/features/`
3. **Implementation**: Branch from `main`, write code + tests
4. **Delivery**: Verify with `pytest` and `bin/gantry validate`, merge to `main`, update `docs/AI_INSIGHTS.md`

## Long-Term Memory

Update `docs/AI_INSIGHTS.md` when encountering project-specific nuances, recurring pitfalls, or architectural constraints.

## Cross-References

- **[AI_DIRECTIVES.md](AI_DIRECTIVES.md)** — Strict behavioral rules for AI agents
- **[WORKFLOW.md](WORKFLOW.md)** — Development workflow and execution SOPs
- **[CONTEXT.md](CONTEXT.md)** — Full architectural context and patterns
- **[docs/AI_INSIGHTS.md](docs/AI_INSIGHTS.md)** — Long-term memory and lessons learned
