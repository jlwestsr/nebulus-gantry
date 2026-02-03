# Project Context: Nebulus Gantry v2

## Overview

Nebulus Gantry is the AI chat interface for the Nebulus Prime ecosystem. It provides a dark-themed, Claude.AI-like conversational UI with streaming LLM responses, long-term memory, multi-user authentication, and an admin control plane for managing services, models, and users.

Version 2 is a complete rewrite. The previous Chainlit/vanilla-JS codebase has been replaced with a modern React + FastAPI stack.

## Architecture

- **Frontend**: React 19, TypeScript, Vite 7, Tailwind CSS v4, Zustand for state management
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2, SQLite
- **LLM**: TabbyAPI (OpenAI-compatible endpoint at `:5000`)
- **Long-Term Memory**: ChromaDB (`:8001`) for vector search, NetworkX for entity knowledge graph
- **Auth**: Session cookies (httponly, bcrypt-hashed passwords), admin/user roles
- **Deployment**: Docker Compose (backend `:8000`, frontend `:3000`)

## Key Patterns

- **API design**: All backend routes are under `/api/` with three routers: `auth`, `chat`, `admin`.
- **Auth flow**: Session token in httponly cookie. `get_current_user` dependency validates on every request.
- **Admin access**: `require_admin` dependency checks `user.role == "admin"`.
- **Streaming**: Chat responses use SSE (`StreamingResponse` with `text/event-stream`). The frontend reads the stream incrementally via `ReadableStream`.
- **LTM injection**: On each message, the backend queries ChromaDB for similar past messages and NetworkX for related entity facts, then prepends them to the system prompt.
- **State stores**: Zustand stores (`authStore`, `chatStore`, `toastStore`, `uiStore`) manage all client state. No prop drilling.
- **Component structure**: Reusable primitives (`Button`, `Input`), composite components (`MessageBubble`, `Sidebar`), and page-level components (`Chat`, `Admin`, `Settings`, `Login`).
- **Error handling**: Backend returns structured HTTP errors; frontend catches them and surfaces via toast notifications.
- **Graceful degradation**: ChromaDB, NetworkX, Docker, and TabbyAPI failures are caught and logged -- the app continues operating without those features.

## Development

```bash
# Backend (local)
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (local)
cd frontend && npm install && npm run dev

# Docker
docker-compose up --build

# Tests
cd backend && python -m pytest tests/ -v
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./data/gantry.db` | Database connection |
| `SECRET_KEY` | `dev-secret-change-in-production` | Session signing |
| `CHROMA_HOST` | `http://localhost:8001` | ChromaDB endpoint |
| `TABBY_HOST` | `http://localhost:5000` | TabbyAPI endpoint |
| `SESSION_EXPIRE_HOURS` | `24` | Cookie lifetime |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL (frontend build) |

## File Map

- `backend/main.py` -- FastAPI app entry point, CORS, router registration
- `backend/config.py` -- `Settings` dataclass loaded from env vars
- `backend/database.py` -- SQLAlchemy engine and session factory
- `backend/models/` -- ORM models: `User`, `Conversation`, `Message`, `Session`
- `backend/schemas/` -- Pydantic request/response schemas
- `backend/services/` -- Business logic: `AuthService`, `ChatService`, `LLMService`, `MemoryService`, `GraphService`, `DockerService`, `ModelService`
- `backend/routers/` -- API routes: `auth.py`, `chat.py`, `admin.py`
- `frontend/src/stores/` -- Zustand stores for auth, chat, toast, UI
- `frontend/src/services/api.ts` -- HTTP client wrapping `fetch`
- `frontend/src/pages/` -- Route-level page components
- `frontend/src/components/` -- Reusable UI components
- `frontend/src/types/api.ts` -- Shared TypeScript interfaces
