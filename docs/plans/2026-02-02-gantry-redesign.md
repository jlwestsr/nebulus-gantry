# Nebulus Gantry Redesign

**Date:** 2026-02-02
**Status:** Approved
**Author:** James West + Claude

## Overview

Nebulus Gantry is a branded AI chat interface for the Nebulus Prime ecosystem. It replaces Open WebUI with a custom, Claude.AI-like experience that includes conversational AI with long-term memory and a control panel for managing the Nebulus stack.

## Goals

1. **Conversational AI** - Clean, minimal chat interface like Claude.AI
2. **Long-term memory** - Hybrid LTM using vectors (ChromaDB) + knowledge graph (NetworkX)
3. **Control panel** - Manage Nebulus services, models, logs from within the UI
4. **Multi-user auth** - Locked-down access with admin/user roles
5. **Brandable** - Custom look and feel for the Nebulus ecosystem

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI + Python 3.12+ |
| Auth | Session cookies (HTTP-only, secure) |
| Database | SQLite + SQLAlchemy |
| Vectors | ChromaDB |
| Graph | NetworkX |
| Streaming | Server-Sent Events (SSE) |
| Deployment | Docker (monorepo) |

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                      Browser                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              React SPA (Vite)                         │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │  │
│  │  │  Chat   │ │ Sidebar │ │ Settings│ │  Admin  │     │  │
│  │  │   View  │ │  List   │ │  Modal  │ │  Panel  │     │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                    REST + SSE
                          │
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Auth API │ │ Chat API │ │Memory API│ │Admin API │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                       │                                     │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐                   │
│  │  SQLite  │ │ ChromaDB  │ │ NetworkX │                   │
│  │ (users,  │ │ (vectors) │ │ (graph)  │                   │
│  │ history) │ │           │ │          │                   │
│  └──────────┘ └───────────┘ └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
                          │
                    Docker Network
                          │
┌─────────────────────────────────────────────────────────────┐
│                  Nebulus Prime Stack                        │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐                   │
│  │ TabbyAPI │ │ ChromaDB  │ │MCP Server│                   │
│  │  (LLM)   │ │ (shared)  │ │ (tools)  │                   │
│  └──────────┘ └───────────┘ └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```text
nebulus-gantry/
├── backend/
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings (env vars)
│   ├── database.py             # SQLite + SQLAlchemy
│   ├── models/                 # Pydantic DTOs + SQLAlchemy entities
│   │   ├── user.py
│   │   ├── conversation.py
│   │   └── message.py
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── chat_service.py
│   │   ├── memory_service.py   # Hybrid LTM
│   │   └── nebulus_service.py  # Control panel
│   ├── routers/                # API endpoints
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── memory.py
│   │   └── admin.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # Reusable UI pieces
│   │   ├── pages/              # Route-level views
│   │   ├── hooks/              # Custom React hooks
│   │   ├── services/           # API client functions
│   │   ├── stores/             # State management
│   │   └── App.tsx
│   ├── package.json
│   └── tailwind.config.js
├── docker-compose.yml
└── Dockerfile
```

## UI Layout

Clean, minimal, Claude.AI-like interface:

```text
┌──────────────────────────────────────────────────────────────┐
│  ┌──────┐                                        ┌────────┐  │
│  │ Logo │        N E B U L U S   G A N T R Y     │  User  │  │
│  └──────┘                                        │  Menu  │  │
├────────────────┬─────────────────────────────────┴────────┤  │
│                │                                          │  │
│  + New Chat    │                                          │  │
│                │                                          │  │
│  Today         │         Welcome back, James.             │  │
│  ├─ Project X  │                                          │  │
│  └─ Quick q... │         How can I help you today?        │  │
│                │                                          │  │
│  Yesterday     │                                          │  │
│  ├─ Debug...   │                                          │  │
│  └─ API design │                                          │  │
│                │                                          │  │
│  ┌──────────┐  ├──────────────────────────────────────────┤  │
│  │ Search   │  │  ┌──────────────────────────────────┐    │  │
│  └──────────┘  │  │  Message Nebulus...              │    │  │
│                │  └──────────────────────────────────┘    │  │
└────────────────┴──────────────────────────────────────────┘
```

### Views

| View | Access | Purpose |
|------|--------|---------|
| Chat | Default | Conversation with AI |
| Search | Sidebar | Find past conversations |
| Settings | User menu | Preferences, theme, model selection |
| Admin Panel | User menu (admin only) | Services, models, logs, users |
| Login | Unauthenticated | Email + password |

### User Menu

- Settings
- Admin Panel *(admin only)*
- Logout

## Data Models

### SQLite Tables

```text
┌─────────────────┐       ┌─────────────────────┐
│     users       │       │      sessions       │
├─────────────────┤       ├─────────────────────┤
│ id (PK)         │──┐    │ id (PK)             │
│ email           │  │    │ user_id (FK)        │
│ password_hash   │  │    │ token               │
│ display_name    │  │    │ expires_at          │
│ role            │  │    └─────────────────────┘
│ created_at      │  │
└─────────────────┘  │    ┌─────────────────────┐
                     │    │   conversations     │
                     └───▶├─────────────────────┤
                          │ id (PK)             │
                          │ user_id (FK)        │
                          │ title               │
                          │ created_at          │
                          │ updated_at          │
                          └─────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────────┐
                          │     messages        │
                          ├─────────────────────┤
                          │ id (PK)             │
                          │ conversation_id (FK)│
                          │ role                │
                          │ content             │
                          │ created_at          │
                          └─────────────────────┘
```

### Hybrid Long-Term Memory

| Store | Technology | Purpose |
|-------|------------|---------|
| Semantic | ChromaDB | Message embeddings for similarity search |
| Associative | NetworkX | Entity relationships and facts |

## API Endpoints

### Auth (`/api/auth`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/login` | Email + password → session cookie |
| POST | `/logout` | Clear session |
| GET | `/me` | Current user info |

### Chat (`/api/chat`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/conversations` | List user's conversations |
| POST | `/conversations` | Create new conversation |
| GET | `/conversations/:id` | Get conversation + messages |
| DELETE | `/conversations/:id` | Delete conversation |
| POST | `/conversations/:id/messages` | Send message, stream response (SSE) |
| GET | `/search?q=` | Search conversation history |

### Admin (`/api/admin`) - Admin Only

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/users` | List all users |
| POST | `/users` | Create user |
| DELETE | `/users/:id` | Remove user |
| GET | `/services` | Nebulus service status |
| POST | `/services/:name/restart` | Restart a service |
| GET | `/models` | List available models |
| POST | `/models/switch` | Change active model |
| GET | `/logs/:service` | Stream logs (SSE) |

## Chat Flow

1. User sends message
2. Save user message to SQLite
3. Query MemoryService for context:
   - ChromaDB: similar past conversations
   - NetworkX: relevant entity facts
4. Build prompt with system message, LTM context, conversation history, user message
5. Stream request to TabbyAPI
6. Stream response to frontend (SSE)
7. On completion:
   - Save assistant message to SQLite
   - Embed message → ChromaDB (async)
   - Extract entities → Update NetworkX graph (async)

## Admin Panel

Four tabs accessible via User Menu → Admin Panel:

### Services Tab

- Status of Nebulus containers (running/stopped)
- Start/stop/restart buttons

### Models Tab

- Currently active model with switch dropdown
- List of downloaded models
- Download new model input

### Logs Tab

- Service selector dropdown
- Live-streaming log output (SSE)
- Clear/pause controls

### Users Tab

- List users (email, role, created date)
- Add user modal
- Delete user with confirmation

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request (validation failed) |
| 401 | Not authenticated |
| 403 | Not authorized |
| 404 | Resource not found |
| 500 | Server error |

### Error Response Format

```json
{
  "error": "not_found",
  "message": "Conversation not found"
}
```

### Graceful Degradation

- ChromaDB down → chat works, LTM disabled with warning
- TabbyAPI down → show "Model unavailable" message
- NetworkX fails → continue without associative memory

## Security

- Passwords hashed with bcrypt
- Session tokens are HTTP-only, secure cookies
- CORS restricted to same origin
- Rate limiting on login endpoint
- Input sanitization on all user inputs
- Admin routes check `user.role === 'admin'`

## Next Steps

1. Set up project structure (monorepo)
2. Implement backend auth + database
3. Implement frontend login + basic layout
4. Implement chat (without LTM)
5. Add LTM (ChromaDB + NetworkX)
6. Add admin panel
7. Dockerize and test end-to-end
