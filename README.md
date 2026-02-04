# Nebulus Gantry v2

A branded AI chat interface for the **Nebulus Prime** ecosystem. Gantry provides a Claude.AI-like conversational UI backed by streaming LLM responses, long-term memory, and an admin control plane.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Vite 7 + Tailwind CSS v4 |
| State | Zustand stores (auth, chat, toast, ui) |
| Backend | FastAPI 0.109 + Python 3.12 + SQLAlchemy 2 |
| Database | SQLite (via aiosqlite) |
| LTM | ChromaDB (vector search) + NetworkX (knowledge graph) |
| Auth | Session cookies (httponly) + bcrypt |
| Streaming | SSE (Server-Sent Events) for chat responses |
| LLM | TabbyAPI (OpenAI-compatible `/v1/chat/completions`) |
| Containers | Docker Compose (backend + frontend) |

## Architecture

```text
 Browser (React SPA)
     |
     | HTTP / SSE
     v
 FastAPI Backend (:8000)
     |
     +---> SQLite          (conversations, messages, users, sessions)
     +---> ChromaDB (:8001) (semantic vector search)
     +---> NetworkX         (entity knowledge graph, persisted as JSON)
     +---> TabbyAPI (:5000) (LLM inference, streaming)
     +---> Docker API       (service management)
```

## Project Structure

```text
nebulus-gantry/
├── backend/
│   ├── main.py                  # FastAPI app + CORS + routers
│   ├── config.py                # Settings dataclass (env vars)
│   ├── database.py              # SQLAlchemy engine + session
│   ├── dependencies.py          # get_db dependency
│   ├── models/
│   │   ├── user.py              # User model (email, role, password_hash)
│   │   ├── conversation.py      # Conversation model
│   │   ├── message.py           # Message model (role, content)
│   │   └── session.py           # Session model (token, expiry)
│   ├── schemas/
│   │   ├── auth.py              # Login/UserResponse schemas
│   │   ├── chat.py              # Conversation/Message/Search schemas
│   │   └── admin.py             # User/Service/Model admin schemas
│   ├── services/
│   │   ├── auth_service.py      # Authentication + session management
│   │   ├── chat_service.py      # Conversation + message CRUD
│   │   ├── llm_service.py       # TabbyAPI streaming client (httpx)
│   │   ├── memory_service.py    # ChromaDB vector embeddings
│   │   ├── graph_service.py     # NetworkX entity graph
│   │   ├── docker_service.py    # Docker container management
│   │   └── model_service.py     # TabbyAPI model listing/switching
│   ├── routers/
│   │   ├── auth.py              # /api/auth/*
│   │   ├── chat.py              # /api/chat/*
│   │   └── admin.py             # /api/admin/* (admin-only)
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout.tsx       # App shell (sidebar + header + content)
│   │   │   ├── Sidebar.tsx      # Conversation list + new chat
│   │   │   ├── MessageList.tsx  # Scrollable message feed
│   │   │   ├── MessageBubble.tsx # Individual message rendering
│   │   │   ├── MessageInput.tsx # Text input with send button
│   │   │   ├── SearchModal.tsx  # Ctrl+K search overlay
│   │   │   ├── Toast.tsx        # Notification toasts
│   │   │   ├── Button.tsx       # Reusable button component
│   │   │   ├── Input.tsx        # Reusable input component
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── admin/
│   │   │       ├── ServicesTab.tsx
│   │   │       ├── ModelsTab.tsx
│   │   │       ├── LogsTab.tsx
│   │   │       └── UsersTab.tsx
│   │   ├── pages/
│   │   │   ├── Chat.tsx         # Main chat view
│   │   │   ├── Login.tsx        # Login form
│   │   │   ├── Admin.tsx        # Admin panel (tabbed)
│   │   │   └── Settings.tsx     # User settings
│   │   ├── stores/
│   │   │   ├── authStore.ts     # Auth state + login/logout
│   │   │   ├── chatStore.ts     # Conversations + messages + streaming
│   │   │   ├── toastStore.ts    # Toast notifications
│   │   │   └── uiStore.ts      # UI state (sidebar, theme)
│   │   ├── services/
│   │   │   └── api.ts           # HTTP client (fetch wrapper)
│   │   └── types/
│   │       └── api.ts           # TypeScript interfaces
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── docs/
│   ├── plans/
│   ├── features/
│   └── bugs/
├── CONTEXT.md
└── README.md
```

## Getting Started

### Prerequisites

- **Docker & Docker Compose** (recommended)
- Or for local dev: **Python 3.12+** and **Node.js 20+**
- External services: **TabbyAPI** (LLM), **ChromaDB** (optional, for LTM)

### Docker (quickest)

```bash
docker-compose up --build
```

- Frontend: <http://localhost:3000>
- Backend: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>

### Local Development

**Backend:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server starts on <http://localhost:5173> by default.

### First Run

The database is auto-created on first startup. Create an admin user by running the seed script or through the API. Default credentials are configured per deployment.

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/gantry.db` | SQLAlchemy database URL |
| `SECRET_KEY` | `dev-secret-change-in-production` | Session signing secret |
| `CHROMA_HOST` | `http://localhost:8001` | ChromaDB endpoint |
| `TABBY_HOST` | `http://localhost:5000` | TabbyAPI endpoint |
| `SESSION_EXPIRE_HOURS` | `24` | Session cookie lifetime |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL (frontend) |

## API Overview

All endpoints require authentication via `session_token` cookie unless noted.

### Auth (`/api/auth`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Authenticate, returns session cookie |
| POST | `/api/auth/logout` | Invalidate session |
| GET | `/api/auth/me` | Get current user profile |

### Chat (`/api/chat`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/chat/search?q=` | Search messages across conversations |
| POST | `/api/chat/conversations` | Create new conversation |
| GET | `/api/chat/conversations` | List user conversations |
| GET | `/api/chat/conversations/:id` | Get conversation with messages |
| DELETE | `/api/chat/conversations/:id` | Delete conversation |
| POST | `/api/chat/conversations/:id/messages` | Send message (SSE streaming response) |

### Admin (`/api/admin`) -- requires admin role

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/users` | List all users |
| POST | `/api/admin/users` | Create user |
| DELETE | `/api/admin/users/:id` | Delete user |
| GET | `/api/admin/services` | List Docker services |
| POST | `/api/admin/services/:name/restart` | Restart a service |
| GET | `/api/admin/models` | List available LLM models |
| POST | `/api/admin/models/switch` | Switch active model |
| GET | `/api/admin/logs/:service` | Stream service logs (SSE) |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |

## Features

- **Chat interface** -- dark theme, Claude.AI-like layout with conversation sidebar
- **Streaming responses** -- real-time SSE from TabbyAPI
- **Long-term memory** -- ChromaDB semantic search + NetworkX entity graph injected into system prompt
- **Conversation search** -- Ctrl+K quick search across all messages
- **Admin panel** -- manage users, Docker services, LLM models, and view logs
- **Settings page** -- profile editing, appearance preferences, model info
- **Toast notifications** -- non-blocking feedback for actions and errors
- **Mobile responsive** -- collapsible sidebar, adaptive layout
- **Multi-user auth** -- session cookies, bcrypt passwords, admin/user roles

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

## License

Proprietary -- West AI Labs.
