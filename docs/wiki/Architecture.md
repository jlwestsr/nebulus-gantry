# Architecture

This document describes the technical architecture of Nebulus Gantry, including system design, component interactions, data flow, and key design decisions.

---

## Overview

Nebulus Gantry is a full-stack web application built with modern technologies:

- **Frontend:** React 19 + TypeScript + Vite
- **Backend:** FastAPI + Python 3.12 + SQLAlchemy
- **Database:** SQLite (or PostgreSQL)
- **Vector Store:** ChromaDB
- **LLM Backend:** OpenAI-compatible API (TabbyAPI, Ollama, etc.)
- **Deployment:** Docker Compose

---

## System Architecture

### High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                        Browser Client                        │
│  ┌────────┬───────────┬──────────┬───────────┬───────────┐  │
│  │ Chat   │ Vault     │ Admin    │ Settings  │ Search    │  │
│  │ Page   │ Page      │ Panel    │ Page      │ (Cmd+K)   │  │
│  └────────┴───────────┴──────────┴───────────┴───────────┘  │
│                    React SPA (Port 3001)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                     HTTP / SSE
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                           │
│                     (Port 8000)                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            API Routers Layer                          │  │
│  │  /auth  /chat  /admin  /documents  /models           │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │          Business Logic Layer                         │  │
│  │  AuthService │ ChatService │ MemoryService │         │  │
│  │  DocumentService │ ModelService │ GraphService       │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Data Access Layer                        │  │
│  │  SQLAlchemy ORM │ Pydantic Schemas                   │  │
│  └───────────────────────────────────────────────────────┘  │
└──────┬────────────┬────────────┬────────────┬──────────────┘
       │            │            │            │
┌──────▼──────┐ ┌──▼──────┐ ┌───▼───────┐ ┌─▼──────────┐
│   SQLite    │ │ ChromaDB│ │ NetworkX  │ │ LLM API    │
│   Database  │ │ Vectors │ │ Graph     │ │ (TabbyAPI) │
│ (Port N/A)  │ │(Port8001│ │ (Memory)  │ │ (Port5000) │
└─────────────┘ └─────────┘ └───────────┘ └────────────┘
```

### Container Architecture

```text
┌────────────────────────────────────────────────────────────┐
│           Docker Network: nebulus-prime_ai-network         │
│                                                            │
│  ┌──────────────────┐        ┌──────────────────┐        │
│  │   Frontend       │        │   Backend        │        │
│  │   Container      │◄──────►│   Container      │        │
│  │   (Node 20)      │        │   (Python 3.12)  │        │
│  │   Port: 3001     │        │   Port: 8000     │        │
│  └──────────────────┘        └────────┬─────────┘        │
│                                       │                   │
│  ┌──────────────────┐        ┌───────▼──────────┐        │
│  │   ChromaDB       │◄──────►│   TabbyAPI       │        │
│  │   (Optional)     │        │   (External)     │        │
│  │   Port: 8001     │        │   Port: 5000     │        │
│  └──────────────────┘        └──────────────────┘        │
│                                                            │
└────────────────────────────────────────────────────────────┘
                         │
                  Reverse Proxy
                  (Nginx/Caddy)
                         │
                    Internet
```

---

## Frontend Architecture

### Technology Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite 7** - Build tool and dev server
- **Tailwind CSS v4** - Styling
- **Zustand** - State management
- **React Router** - Client-side routing

### Directory Structure

```text
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Chat/            # Chat-specific components
│   │   ├── Admin/           # Admin panel components
│   │   ├── Layout/          # Layout components (Sidebar, Header)
│   │   └── Shared/          # Shared components (Button, Modal, etc.)
│   ├── pages/               # Route-level page components
│   │   ├── ChatPage.tsx
│   │   ├── AdminDashboard.tsx
│   │   ├── KnowledgeVault.tsx
│   │   └── LoginPage.tsx
│   ├── stores/              # Zustand state stores
│   │   ├── authStore.ts     # Authentication state
│   │   ├── chatStore.ts     # Chat state
│   │   ├── toastStore.ts    # Notifications
│   │   └── uiStore.ts       # UI state
│   ├── services/            # API client
│   │   └── api.ts           # HTTP client wrapper
│   ├── types/               # TypeScript type definitions
│   │   └── api.ts           # API response types
│   ├── hooks/               # Custom React hooks
│   ├── utils/               # Utility functions
│   ├── App.tsx              # Root component
│   └── main.tsx             # Entry point
├── public/                  # Static assets
├── vite.config.ts           # Vite configuration
└── tsconfig.json            # TypeScript configuration
```

### State Management

Using Zustand for global state:

```typescript
// stores/chatStore.ts
import { create } from 'zustand';

interface ChatStore {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  setConversations: (convs: Conversation[]) => void;
  addMessage: (message: Message) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  setConversations: (convs) => set({ conversations: convs }),
  addMessage: (msg) => set((state) => ({
    messages: [...state.messages, msg]
  })),
}));
```

### API Communication

```typescript
// services/api.ts
class APIClient {
  private baseURL = import.meta.env.VITE_API_URL;

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      credentials: 'include',  // Send cookies
    });
    return response.json();
  }

  async post<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    return response.json();
  }

  // SSE streaming
  streamChat(conversationId: number): EventSource {
    return new EventSource(
      `${this.baseURL}/chat/stream/${conversationId}`,
      { withCredentials: true }
    );
  }
}
```

### Routing

```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute />}>
          <Route index element={<ChatPage />} />
          <Route path="chat/:id" element={<ChatPage />} />
          <Route path="vault" element={<KnowledgeVault />} />
          <Route path="admin" element={<AdminDashboard />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

---

## Backend Architecture

### Technology Stack

- **FastAPI** - Web framework
- **Python 3.12** - Language
- **SQLAlchemy 2** - ORM
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **bcrypt** - Password hashing

### Directory Structure

```text
backend/
├── routers/                 # API endpoint definitions
│   ├── auth.py              # Authentication routes
│   ├── chat.py              # Chat routes
│   ├── admin.py             # Admin routes
│   ├── documents.py         # Document upload/retrieval
│   ├── models.py            # Model management
│   └── personas.py          # Persona management
├── services/                # Business logic layer
│   ├── auth_service.py      # User authentication
│   ├── chat_service.py      # Chat orchestration
│   ├── llm_service.py       # LLM communication
│   ├── memory_service.py    # ChromaDB integration
│   ├── graph_service.py     # Knowledge graph
│   ├── document_service.py  # Document processing
│   ├── model_service.py     # Model switching
│   └── docker_service.py    # Docker API integration
├── models/                  # SQLAlchemy ORM models
│   ├── user.py              # User model
│   ├── conversation.py      # Conversation model
│   ├── message.py           # Message model
│   ├── document.py          # Document model
│   ├── session.py           # Session model
│   └── persona.py           # Persona model
├── schemas/                 # Pydantic request/response schemas
│   ├── auth.py              # Auth schemas
│   ├── chat.py              # Chat schemas
│   ├── admin.py             # Admin schemas
│   └── document.py          # Document schemas
├── main.py                  # Application entry point
├── config.py                # Configuration settings
├── database.py              # Database setup
├── dependencies.py          # FastAPI dependencies
└── utils.py                 # Utility functions
```

### Layered Architecture

#### 1. Router Layer (API Endpoints)

```python
# routers/chat.py
from fastapi import APIRouter, Depends
from backend.services.chat_service import ChatService
from backend.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/")
async def send_message(
    request: ChatRequest,
    chat_service: ChatService = Depends(),
) -> ChatResponse:
    """Send a message and get AI response."""
    return await chat_service.send_message(request)
```

#### 2. Service Layer (Business Logic)

```python
# services/chat_service.py
class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.llm_service = LLMService()
        self.memory_service = MemoryService()

    async def send_message(self, request: ChatRequest) -> ChatResponse:
        # 1. Save user message
        user_msg = self.save_message(request)

        # 2. Retrieve context from memory
        context = self.memory_service.search(request.content)

        # 3. Generate AI response
        ai_response = await self.llm_service.generate(
            messages=request.messages,
            context=context
        )

        # 4. Save AI message
        ai_msg = self.save_message(ai_response)

        # 5. Store in vector database
        self.memory_service.store(ai_msg)

        return ChatResponse(message=ai_msg)
```

#### 3. Data Access Layer (ORM Models)

```python
# models/message.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
```

### Dependency Injection

```python
# dependencies.py
from fastapi import Depends, HTTPException, Cookie
from sqlalchemy.orm import Session

def get_db() -> Session:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    session_id: str = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    """Authenticated user dependency."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = db.query(Session).filter(Session.id == session_id).first()
    if not session or session.is_expired():
        raise HTTPException(status_code=401, detail="Session expired")

    return session.user

def require_admin(user: User = Depends(get_current_user)) -> User:
    """Admin-only dependency."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user
```

---

## Data Flow

### Chat Message Flow

```text
1. User Types Message
   ↓
2. Frontend (React)
   - Validates input
   - Sends POST /chat
   ↓
3. Backend Router
   - Validates request (Pydantic)
   - Checks authentication
   ↓
4. Chat Service
   - Saves user message to DB
   - Retrieves memory context
   ↓
5. Memory Service
   - Searches ChromaDB vectors
   - Queries knowledge graph
   - Returns relevant context
   ↓
6. LLM Service
   - Prepares prompt with context
   - Calls TabbyAPI (streaming)
   - Returns token stream
   ↓
7. Chat Service
   - Accumulates tokens
   - Saves AI response to DB
   - Stores in ChromaDB
   ↓
8. Backend Router
   - Returns response
   ↓
9. Frontend
   - Updates UI with AI message
   - Stores in local state
```

### SSE Streaming Flow

```text
1. Frontend Opens EventSource
   GET /chat/stream/{conversation_id}
   ↓
2. Backend Router
   - Validates auth
   - Returns StreamingResponse
   ↓
3. Chat Service Generates Tokens
   for token in llm_service.stream():
       yield f"data: {token}\n\n"
   ↓
4. Frontend Receives Events
   eventSource.onmessage = (event) => {
       appendToken(event.data)
   }
   ↓
5. Connection Closes on Complete
   yield "data: [DONE]\n\n"
```

### Authentication Flow

```text
1. User Submits Login Form
   POST /auth/login
   { email, password }
   ↓
2. Auth Service
   - Query user by email
   - Verify password (bcrypt)
   - Create session
   ↓
3. Backend Router
   - Set session cookie (httponly)
   - Return user data
   ↓
4. Frontend
   - Store user in authStore
   - Redirect to chat
   ↓
5. Subsequent Requests
   - Include session cookie
   - Backend validates session
   - Returns user from DB
```

### Document Upload Flow

```text
1. User Uploads File
   ↓
2. Frontend
   - FormData with file
   - POST /documents/upload
   ↓
3. Document Service
   - Save file to disk
   - Extract text content
   - Chunk into segments
   ↓
4. Memory Service
   - Generate embeddings
   - Store in ChromaDB
   - Link to document ID
   ↓
5. Document Service
   - Create document record
   - Return status
   ↓
6. Frontend
   - Show success
   - Update document list
```

---

## Database Schema

### Entity-Relationship Diagram

```text
┌──────────────┐         ┌──────────────────┐
│    User      │         │   Conversation   │
├──────────────┤    1:N  ├──────────────────┤
│ id (PK)      │◄────────┤ id (PK)          │
│ email        │         │ user_id (FK)     │
│ password_hash│         │ title            │
│ display_name │         │ created_at       │
│ role         │         │ updated_at       │
│ created_at   │         │ pinned           │
└──────────────┘         └────────┬─────────┘
       │                          │
       │ 1:N                      │ 1:N
       │                          │
       │                 ┌────────▼─────────┐
       │                 │    Message       │
       │                 ├──────────────────┤
       │                 │ id (PK)          │
       │                 │ conversation_id  │
       │                 │ role             │
       │                 │ content          │
       │                 │ created_at       │
       │                 └──────────────────┘
       │
       │ 1:N
       │
┌──────▼───────┐         ┌──────────────────┐
│   Session    │         │   Document       │
├──────────────┤         ├──────────────────┤
│ id (PK)      │    1:N  │ id (PK)          │
│ user_id (FK) │◄────────┤ user_id (FK)     │
│ created_at   │         │ filename         │
│ expires_at   │         │ content_type     │
└──────────────┘         │ size_bytes       │
                         │ status           │
                         │ created_at       │
                         └──────────────────┘
```

### Key Tables

#### users

| Column        | Type      | Description           |
|---------------|-----------|-----------------------|
| id            | INTEGER   | Primary key           |
| email         | VARCHAR   | Unique email          |
| password_hash | VARCHAR   | bcrypt hash           |
| display_name  | VARCHAR   | Display name          |
| role          | VARCHAR   | 'admin' or 'user'     |
| created_at    | TIMESTAMP | Creation timestamp    |

#### conversations

| Column     | Type      | Description              |
|------------|-----------|--------------------------|
| id         | INTEGER   | Primary key              |
| user_id    | INTEGER   | Foreign key to users     |
| title      | VARCHAR   | Conversation title       |
| created_at | TIMESTAMP | Creation timestamp       |
| updated_at | TIMESTAMP | Last message timestamp   |
| pinned     | BOOLEAN   | Pin to top of list       |

#### messages

| Column          | Type      | Description                   |
|-----------------|-----------|-------------------------------|
| id              | INTEGER   | Primary key                   |
| conversation_id | INTEGER   | Foreign key to conversations  |
| role            | VARCHAR   | 'user' or 'assistant'         |
| content         | TEXT      | Message content               |
| created_at      | TIMESTAMP | Creation timestamp            |

#### sessions

| Column     | Type      | Description           |
|------------|-----------|-----------------------|
| id         | VARCHAR   | Session ID (UUID)     |
| user_id    | INTEGER   | Foreign key to users  |
| created_at | TIMESTAMP | Creation timestamp    |
| expires_at | TIMESTAMP | Expiration timestamp  |

#### documents

| Column       | Type      | Description              |
|--------------|-----------|--------------------------|
| id           | INTEGER   | Primary key              |
| user_id      | INTEGER   | Foreign key to users     |
| filename     | VARCHAR   | Original filename        |
| content_type | VARCHAR   | MIME type                |
| size_bytes   | INTEGER   | File size                |
| status       | VARCHAR   | 'processing' or 'ready'  |
| created_at   | TIMESTAMP | Upload timestamp         |

---

## External Services

### ChromaDB (Vector Store)

**Purpose:** Store and search message embeddings for long-term memory.

**Connection:**

```python
# services/memory_service.py
import chromadb

client = chromadb.HttpClient(
    host=CHROMA_HOST,
    port=CHROMA_PORT
)

collection = client.get_or_create_collection(
    name="conversations",
    metadata={"hnsw:space": "cosine"}
)
```

**Operations:**

- `add()` - Store message embeddings
- `query()` - Semantic search for context
- `delete()` - Remove old embeddings
- `get()` - Retrieve by ID

### TabbyAPI (LLM Backend)

**Purpose:** Generate AI responses via OpenAI-compatible API.

**Connection:**

```python
# services/llm_service.py
import httpx

async def generate(messages: List[dict]) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TABBY_HOST}/v1/chat/completions",
            json={
                "model": "default",
                "messages": messages,
                "stream": False,
            }
        )
        return response.json()["choices"][0]["message"]["content"]
```

**Streaming:**

```python
async def stream(messages: List[dict]):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{TABBY_HOST}/v1/chat/completions",
            json={"messages": messages, "stream": True}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line[6:]  # Remove "data: " prefix
```

### NetworkX (Knowledge Graph)

**Purpose:** Extract and store entity relationships from conversations.

**Structure:**

```python
# services/graph_service.py
import networkx as nx

graph = nx.DiGraph()

# Add entities
graph.add_node("Python", type="technology")
graph.add_node("FastAPI", type="framework")

# Add relationships
graph.add_edge("FastAPI", "Python", relation="built_with")

# Query
neighbors = list(graph.neighbors("Python"))
path = nx.shortest_path(graph, "FastAPI", "Python")
```

---

## Security Architecture

### Authentication

- Session-based auth with httponly cookies
- bcrypt password hashing (cost factor 12)
- Session expiration (configurable, default 24h)
- CSRF protection via SameSite cookies

### Authorization

- Role-based access control (admin vs. user)
- Dependency injection for route protection
- User-scoped data access (users only see their own data)

### Data Security

- SQL injection protection (SQLAlchemy ORM)
- XSS protection (React escapes by default)
- Input validation (Pydantic schemas)
- CORS configured for specific origins

---

## Design Patterns

### 1. Dependency Injection

FastAPI's DI system for services and auth:

```python
@router.get("/conversations")
def get_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return db.query(Conversation).filter(
        Conversation.user_id == user.id
    ).all()
```

### 2. Service Layer Pattern

Business logic isolated from routes:

```python
# routers/chat.py (thin)
@router.post("/chat")
async def chat(request: ChatRequest, service: ChatService = Depends()):
    return await service.handle_chat(request)

# services/chat_service.py (thick)
class ChatService:
    async def handle_chat(self, request):
        # Complex logic here
        pass
```

### 3. Repository Pattern

Data access abstracted:

```python
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def create(self, user_data: dict) -> User:
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        return user
```

### 4. Factory Pattern

For creating services with dependencies:

```python
def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    llm_service = LLMService()
    memory_service = MemoryService()
    return ChatService(db, llm_service, memory_service)
```

---

## Performance Considerations

### Frontend

- Code splitting via Vite
- Lazy loading for heavy components
- Virtual scrolling for long lists
- Debounced search inputs
- Memoized components

### Backend

- Async I/O throughout
- Connection pooling
- Database indexes on foreign keys
- Streaming responses for chat
- Background tasks for heavy operations

### Database

- WAL mode for SQLite concurrency
- Indexed columns for common queries
- Pagination for large result sets
- PostgreSQL recommended for production

---

## Scalability

### Horizontal Scaling

- Stateless backend (sessions in DB)
- Multiple backend instances behind load balancer
- Shared database and ChromaDB instances

### Vertical Scaling

- Increase Uvicorn workers
- Tune database connection pool
- Optimize ChromaDB collection size

---

## Monitoring & Observability

### Logging

- Structured JSON logs
- Request/response logging
- Error tracking with stack traces
- Log levels: DEBUG, INFO, WARNING, ERROR

### Metrics

- Request latency
- Error rates
- Database query times
- LLM response times

### Health Checks

- `/health` endpoint for backend
- Database connectivity check
- ChromaDB connectivity check
- LLM backend connectivity check

---

## Future Architecture Considerations

### Planned Features

- **Multi-modal:** Image upload and vision models
- **Personas:** Custom system prompts per conversation
- **Advanced RAG:** Hybrid search (vector + keyword)
- **Real-time collaboration:** WebSocket for shared chats

### Scalability Improvements

- Message queue (Celery/RabbitMQ) for background tasks
- Redis for distributed caching
- Read replicas for database
- CDN for static assets

---

## Related Documentation

- **[API Reference](API-Reference)** - Complete endpoint documentation
- **[Development Setup](Development-Setup)** - Local development guide
- **[Scaling & Performance](Scaling-Performance)** - Optimization strategies
- **[Testing](Testing)** - Testing architecture and practices

---

**[← Back to Scaling & Performance](Scaling-Performance)** | **[Next: API Reference →](API-Reference)**
