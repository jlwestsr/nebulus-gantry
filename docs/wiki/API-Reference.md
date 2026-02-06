# API Reference

Complete REST API documentation for Nebulus Gantry, including authentication, chat, documents, admin operations, and SSE streaming.

---

## Base URL

```text
http://localhost:8000  # Development
https://yourdomain.com # Production
```

All endpoints are prefixed with `/api` unless otherwise noted.

---

## Authentication

All endpoints except `/api/auth/login` and `/api/auth/register` require authentication via session cookie.

### POST /api/auth/login

Authenticate user and create session.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response:** `200 OK`

```json
{
  "id": 1,
  "email": "user@example.com",
  "display_name": "John Doe",
  "role": "user"
}
```

**Sets Cookie:** `session_id=<uuid>` (httponly, secure)

**Errors:**

- `401 Unauthorized` - Invalid credentials
- `422 Unprocessable Entity` - Validation error

**Example:**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  -c cookies.txt
```

### POST /api/auth/register

Create new user account.

**Request Body:**

```json
{
  "email": "newuser@example.com",
  "password": "secure-password",
  "display_name": "New User"
}
```

**Response:** `201 Created`

```json
{
  "id": 2,
  "email": "newuser@example.com",
  "display_name": "New User",
  "role": "user"
}
```

**Errors:**

- `400 Bad Request` - Email already exists
- `422 Unprocessable Entity` - Validation error

### POST /api/auth/logout

End current session.

**Response:** `200 OK`

```json
{
  "message": "Logged out successfully"
}
```

**Clears Cookie:** `session_id`

### GET /api/auth/me

Get current authenticated user.

**Response:** `200 OK`

```json
{
  "id": 1,
  "email": "user@example.com",
  "display_name": "John Doe",
  "role": "user"
}
```

**Errors:**

- `401 Unauthorized` - Not authenticated or session expired

---

## Conversations

### GET /api/chat/conversations

List all conversations for authenticated user.

**Response:** `200 OK`

```json
{
  "conversations": [
    {
      "id": 1,
      "title": "Python FastAPI Questions",
      "created_at": "2026-02-06T10:00:00Z",
      "updated_at": "2026-02-06T12:30:00Z",
      "pinned": false,
      "message_count": 24
    },
    {
      "id": 2,
      "title": "Docker Debugging",
      "created_at": "2026-02-05T14:00:00Z",
      "updated_at": "2026-02-06T09:15:00Z",
      "pinned": true,
      "message_count": 8
    }
  ]
}
```

**Query Parameters:**

- `limit` (optional, default: 50) - Max conversations to return
- `offset` (optional, default: 0) - Pagination offset

**Example:**

```bash
curl http://localhost:8000/api/chat/conversations \
  -b cookies.txt
```

### POST /api/chat/conversations

Create new conversation.

**Request Body:**

```json
{
  "title": "New Conversation"
}
```

**Response:** `201 Created`

```json
{
  "id": 3,
  "title": "New Conversation",
  "created_at": "2026-02-06T13:00:00Z",
  "updated_at": "2026-02-06T13:00:00Z",
  "pinned": false,
  "message_count": 0
}
```

### GET /api/chat/conversations/{id}

Get single conversation with messages.

**Path Parameters:**

- `id` (integer) - Conversation ID

**Response:** `200 OK`

```json
{
  "id": 1,
  "title": "Python FastAPI Questions",
  "created_at": "2026-02-06T10:00:00Z",
  "updated_at": "2026-02-06T12:30:00Z",
  "pinned": false,
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "How do I create a FastAPI endpoint?",
      "created_at": "2026-02-06T10:00:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "To create a FastAPI endpoint...",
      "created_at": "2026-02-06T10:00:15Z"
    }
  ]
}
```

**Errors:**

- `404 Not Found` - Conversation doesn't exist or doesn't belong to user

### PUT /api/chat/conversations/{id}

Update conversation (title or pinned status).

**Request Body:**

```json
{
  "title": "Updated Title",
  "pinned": true
}
```

**Response:** `200 OK`

```json
{
  "id": 1,
  "title": "Updated Title",
  "pinned": true
}
```

### DELETE /api/chat/conversations/{id}

Delete conversation and all messages.

**Response:** `204 No Content`

**Errors:**

- `404 Not Found` - Conversation doesn't exist

### GET /api/chat/conversations/{id}/export

Export conversation as JSON or PDF.

**Query Parameters:**

- `format` (required) - "json" or "pdf"

**Response (JSON):** `200 OK`

```json
{
  "conversation": {
    "id": 1,
    "title": "Conversation Title",
    "created_at": "2026-02-06T10:00:00Z",
    "messages": [...]
  },
  "user": {
    "email": "user@example.com",
    "display_name": "User"
  },
  "exported_at": "2026-02-06T15:00:00Z"
}
```

**Response (PDF):** `200 OK`

- Content-Type: `application/pdf`
- Binary PDF file

---

## Chat Messages

### POST /api/chat/send

Send message and get AI response.

**Request Body:**

```json
{
  "conversation_id": 1,
  "content": "What is FastAPI?",
  "use_memory": true,
  "use_knowledge_vault": false
}
```

**Response:** `200 OK`

```json
{
  "user_message": {
    "id": 10,
    "role": "user",
    "content": "What is FastAPI?",
    "created_at": "2026-02-06T13:30:00Z"
  },
  "assistant_message": {
    "id": 11,
    "role": "assistant",
    "content": "FastAPI is a modern, fast web framework...",
    "created_at": "2026-02-06T13:30:05Z"
  }
}
```

**Request Fields:**

- `conversation_id` (integer, required) - Target conversation
- `content` (string, required) - User message content
- `use_memory` (boolean, optional, default: true) - Include LTM context
- `use_knowledge_vault` (boolean, optional, default: false) - Include document context

**Errors:**

- `404 Not Found` - Conversation doesn't exist
- `500 Internal Server Error` - LLM service unavailable

### GET /api/chat/stream/{conversation_id}

Stream AI responses via Server-Sent Events (SSE).

**Path Parameters:**

- `conversation_id` (integer) - Conversation ID

**Response:** `200 OK` (SSE stream)

```text
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"type": "token", "content": "FastAPI"}

data: {"type": "token", "content": " is"}

data: {"type": "token", "content": " a"}

data: {"type": "done", "message_id": 11}
```

**Event Types:**

- `token` - Individual token from LLM
- `done` - Stream complete, includes final message ID
- `error` - Error occurred

**Example (JavaScript):**

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/chat/stream/1',
  { withCredentials: true }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'token') {
    appendToken(data.content);
  } else if (data.type === 'done') {
    console.log('Stream complete:', data.message_id);
    eventSource.close();
  } else if (data.type === 'error') {
    console.error('Stream error:', data.error);
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};
```

**Example (Python):**

```python
import requests

response = requests.get(
    'http://localhost:8000/api/chat/stream/1',
    stream=True,
    cookies={'session_id': 'your-session-id'}
)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            data = json.loads(line[6:])
            if data['type'] == 'token':
                print(data['content'], end='', flush=True)
            elif data['type'] == 'done':
                print(f"\nMessage ID: {data['message_id']}")
                break
```

### GET /api/chat/search

Search across message content and conversation titles.

**Query Parameters:**

- `q` (string, required) - Search query

**Response:** `200 OK`

```json
{
  "results": [
    {
      "conversation_id": 1,
      "conversation_title": "Python Questions",
      "message_id": 5,
      "content": "How do I use FastAPI with SQLAlchemy?",
      "role": "user",
      "created_at": "2026-02-06T10:15:00Z",
      "snippet": "...use FastAPI with SQLAlchemy..."
    }
  ]
}
```

---

## Documents (Knowledge Vault)

### POST /api/documents/upload

Upload document for RAG.

**Request:** `multipart/form-data`

- `file` (file, required) - Document to upload
- `collection` (string, optional) - Collection name (default: "default")

**Response:** `201 Created`

```json
{
  "id": 1,
  "filename": "manual.pdf",
  "content_type": "application/pdf",
  "size_bytes": 524288,
  "status": "processing",
  "collection": "default",
  "created_at": "2026-02-06T14:00:00Z"
}
```

**Status Values:**

- `processing` - Document being chunked and indexed
- `ready` - Available for RAG queries
- `error` - Processing failed

**Example:**

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -b cookies.txt \
  -F "file=@manual.pdf" \
  -F "collection=manuals"
```

**Supported File Types:**

- PDF (`.pdf`)
- Word (`.docx`)
- Text (`.txt`, `.md`)
- CSV (`.csv`)

### GET /api/documents

List uploaded documents.

**Query Parameters:**

- `collection` (string, optional) - Filter by collection
- `status` (string, optional) - Filter by status

**Response:** `200 OK`

```json
{
  "documents": [
    {
      "id": 1,
      "filename": "manual.pdf",
      "content_type": "application/pdf",
      "size_bytes": 524288,
      "status": "ready",
      "collection": "manuals",
      "chunk_count": 42,
      "created_at": "2026-02-06T14:00:00Z"
    }
  ]
}
```

### GET /api/documents/{id}

Get document details.

**Response:** `200 OK`

```json
{
  "id": 1,
  "filename": "manual.pdf",
  "content_type": "application/pdf",
  "size_bytes": 524288,
  "status": "ready",
  "collection": "manuals",
  "chunk_count": 42,
  "created_at": "2026-02-06T14:00:00Z",
  "chunks": [
    {
      "id": 1,
      "content": "Chapter 1: Introduction...",
      "page": 1,
      "chunk_index": 0
    }
  ]
}
```

### DELETE /api/documents/{id}

Delete document and remove from vector store.

**Response:** `204 No Content`

### POST /api/documents/search

Search documents semantically.

**Request Body:**

```json
{
  "query": "How do I configure the database?",
  "collection": "manuals",
  "limit": 5
}
```

**Response:** `200 OK`

```json
{
  "results": [
    {
      "document_id": 1,
      "filename": "manual.pdf",
      "chunk_id": 15,
      "content": "Database Configuration: To configure...",
      "score": 0.87,
      "page": 8
    }
  ]
}
```

### GET /api/documents/collections

List all collections.

**Response:** `200 OK`

```json
{
  "collections": [
    {
      "name": "default",
      "document_count": 5,
      "chunk_count": 120
    },
    {
      "name": "manuals",
      "document_count": 3,
      "chunk_count": 85
    }
  ]
}
```

---

## Models

### GET /api/models

List available LLM models.

**Response:** `200 OK`

```json
{
  "models": [
    {
      "id": "qwen2.5-coder-7b",
      "name": "Qwen2.5 Coder 7B",
      "parameters": "7B",
      "context_length": 32768,
      "loaded": true
    },
    {
      "id": "llama-3.1-8b",
      "name": "Llama 3.1 8B",
      "parameters": "8B",
      "context_length": 8192,
      "loaded": false
    }
  ],
  "current": "qwen2.5-coder-7b"
}
```

### POST /api/models/load

Load/switch to different model.

**Request Body:**

```json
{
  "model_id": "llama-3.1-8b"
}
```

**Response:** `200 OK`

```json
{
  "message": "Model loaded successfully",
  "model_id": "llama-3.1-8b"
}
```

**Note:** Requires TabbyAPI backend. Returns `501 Not Implemented` with other backends.

---

## Admin Endpoints

All admin endpoints require `admin` role.

### GET /api/admin/users

List all users.

**Response:** `200 OK`

```json
{
  "users": [
    {
      "id": 1,
      "email": "admin@example.com",
      "display_name": "Admin",
      "role": "admin",
      "created_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "email": "user@example.com",
      "display_name": "User",
      "role": "user",
      "created_at": "2026-02-01T10:00:00Z"
    }
  ]
}
```

### POST /api/admin/users

Create new user.

**Request Body:**

```json
{
  "email": "newuser@example.com",
  "password": "secure-password",
  "display_name": "New User",
  "role": "user"
}
```

**Response:** `201 Created`

```json
{
  "id": 3,
  "email": "newuser@example.com",
  "display_name": "New User",
  "role": "user"
}
```

### PUT /api/admin/users/{id}

Update user.

**Request Body:**

```json
{
  "display_name": "Updated Name",
  "role": "admin"
}
```

**Response:** `200 OK`

### DELETE /api/admin/users/{id}

Delete user and all their data.

**Response:** `204 No Content`

### GET /api/admin/services

Get Docker service status.

**Response:** `200 OK`

```json
{
  "services": [
    {
      "name": "gantry-backend",
      "status": "running",
      "health": "healthy",
      "uptime": "2 days"
    },
    {
      "name": "gantry-frontend",
      "status": "running",
      "health": "healthy",
      "uptime": "2 days"
    },
    {
      "name": "chromadb",
      "status": "running",
      "health": "healthy",
      "uptime": "5 days"
    }
  ]
}
```

### POST /api/admin/services/{name}/restart

Restart Docker service.

**Response:** `200 OK`

```json
{
  "message": "Service restarted successfully",
  "service": "gantry-backend"
}
```

### GET /api/admin/logs

Stream container logs via SSE.

**Query Parameters:**

- `service` (string, required) - Service name
- `tail` (integer, optional, default: 100) - Number of recent lines

**Response:** SSE stream

```text
data: {"timestamp": "2026-02-06T14:30:00Z", "message": "INFO: Started server"}

data: {"timestamp": "2026-02-06T14:30:05Z", "message": "INFO: Received request"}
```

### GET /api/admin/stats

Get system statistics.

**Response:** `200 OK`

```json
{
  "users": {
    "total": 10,
    "admin": 2,
    "user": 8
  },
  "conversations": {
    "total": 234,
    "last_24h": 15
  },
  "messages": {
    "total": 5678,
    "last_24h": 123
  },
  "documents": {
    "total": 42,
    "total_bytes": 52428800
  },
  "system": {
    "cpu_percent": 25.4,
    "memory_percent": 45.2,
    "disk_percent": 35.8
  }
}
```

### POST /api/admin/export

Export all conversations (admin bulk export).

**Request Body:**

```json
{
  "format": "json",
  "user_ids": [1, 2, 3]
}
```

**Response:** `200 OK`

- Returns ZIP file with all conversations

---

## Personas

### GET /api/personas

List available personas.

**Response:** `200 OK`

```json
{
  "personas": [
    {
      "id": 1,
      "name": "Code Assistant",
      "system_prompt": "You are an expert programmer...",
      "is_default": true,
      "created_at": "2026-02-01T00:00:00Z"
    }
  ]
}
```

### POST /api/personas

Create custom persona.

**Request Body:**

```json
{
  "name": "Python Expert",
  "system_prompt": "You are a Python expert specializing in...",
  "is_default": false
}
```

**Response:** `201 Created`

### PUT /api/conversations/{id}/persona

Set persona for conversation.

**Request Body:**

```json
{
  "persona_id": 2
}
```

**Response:** `200 OK`

---

## Health & Status

### GET /health

Health check endpoint (no auth required).

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "timestamp": "2026-02-06T15:00:00Z",
  "services": {
    "database": "connected",
    "chromadb": "connected",
    "llm": "connected"
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message description"
}
```

### Common Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `201` | Created | Resource created |
| `204` | No Content | Successful deletion |
| `400` | Bad Request | Invalid request data |
| `401` | Unauthorized | Authentication required |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `422` | Unprocessable Entity | Validation error |
| `500` | Internal Server Error | Server error |
| `501` | Not Implemented | Feature not available |
| `503` | Service Unavailable | External service down |

---

## Rate Limiting

Default limits (configurable):

- Auth endpoints: 5 requests/minute
- Chat endpoints: 10 requests/minute
- Other endpoints: 100 requests/minute

**Rate limit headers:**

```text
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1675701600
```

**Rate limit exceeded response:**

```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

---

## Authentication Examples

### cURL

```bash
# Login and save session
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  -c cookies.txt

# Use session for authenticated request
curl http://localhost:8000/api/chat/conversations \
  -b cookies.txt
```

### Python

```python
import requests

# Login
session = requests.Session()
response = session.post(
    'http://localhost:8000/api/auth/login',
    json={'email': 'user@example.com', 'password': 'password'}
)

# Session automatically includes cookies
conversations = session.get(
    'http://localhost:8000/api/chat/conversations'
).json()
```

### JavaScript

```javascript
// Login
const response = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',  // Important!
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password'
  })
});

// Subsequent requests
const conversations = await fetch(
  'http://localhost:8000/api/chat/conversations',
  { credentials: 'include' }
).then(res => res.json());
```

---

## Interactive Documentation

Visit these URLs when backend is running:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

Both provide interactive API testing and schema exploration.

---

## WebSocket Support

Currently, all real-time features use SSE (Server-Sent Events), not WebSockets. SSE is simpler and sufficient for one-way streaming from server to client.

Future versions may add WebSocket support for bi-directional features like collaborative editing.

---

## Pagination

Endpoints that return lists support pagination:

**Query Parameters:**

- `limit` (integer, default: 50, max: 100) - Items per page
- `offset` (integer, default: 0) - Items to skip

**Response includes pagination metadata:**

```json
{
  "items": [...],
  "total": 234,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

---

## Related Documentation

- **[Architecture](Architecture)** - System design and data flow
- **[Development Setup](Development-Setup)** - Local API development
- **[Testing](Testing)** - API testing examples

---

**[← Back to Architecture](Architecture)** | **[Next: Development Setup →](Development-Setup)**
