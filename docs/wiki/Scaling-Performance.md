# Scaling & Performance

This guide covers strategies for optimizing Nebulus Gantry for high-traffic production deployments, from single-server optimizations to multi-instance scaling.

---

## Performance Baseline

### Expected Performance (Single Instance)

**Hardware:** 4 CPU cores, 8GB RAM, SSD

| Metric | Value |
|--------|-------|
| **Concurrent Users** | 50-100 |
| **Requests/second** | 100-200 |
| **Chat Response Time** | 1-3s (depends on LLM) |
| **Database Queries/sec** | 500+ |
| **Memory Usage** | 2-4GB |

**Bottlenecks:**

1. LLM inference speed (external service)
2. Database I/O (SQLite write locks)
3. ChromaDB vector search (for large collections)

---

## Database Optimization

### SQLite Tuning

#### 1. Enable WAL Mode

Write-Ahead Logging improves concurrency:

```python
# backend/database.py
from sqlalchemy import create_engine, event

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30.0,  # Longer timeout
    }
)

# Enable WAL mode
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()
```

#### 2. Connection Pooling

```python
# backend/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Max persistent connections
    max_overflow=40,        # Max additional connections
    pool_pre_ping=True,     # Verify connection health
    pool_recycle=3600,      # Recycle connections hourly
)
```

#### 3. Add Database Indexes

```python
# backend/models/message.py
from sqlalchemy import Index

class Message(Base):
    __tablename__ = "messages"

    # ... existing columns

    # Add indexes for common queries
    __table_args__ = (
        Index('idx_conversation_created', 'conversation_id', 'created_at'),
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_role', 'role'),
    )
```

Run migration:

```bash
# Create migration script
docker compose exec backend python -c "
from backend.database import get_engine, Base
from backend.models import *

engine = get_engine()
Base.metadata.create_all(bind=engine)
print('Indexes created')
"
```

#### 4. Query Optimization

**Before:**

```python
# Loads all messages into memory
messages = db.query(Message).filter(
    Message.conversation_id == conv_id
).all()
```

**After:**

```python
# Pagination
messages = db.query(Message).filter(
    Message.conversation_id == conv_id
).order_by(Message.created_at.desc()).limit(50).all()

# Lazy loading
messages = db.query(Message).filter(
    Message.conversation_id == conv_id
).yield_per(100)  # Stream results
```

### Migrate to PostgreSQL

For production scale, PostgreSQL is recommended.

#### 1. Install PostgreSQL

```bash
# Docker
docker run -d \
  --name gantry-postgres \
  --network nebulus-prime_ai-network \
  -e POSTGRES_DB=gantry \
  -e POSTGRES_USER=gantry_user \
  -e POSTGRES_PASSWORD=secure-password \
  -v postgres-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:16-alpine
```

#### 2. Update Configuration

```bash
# .env
DATABASE_URL=postgresql://gantry_user:secure-password@postgres:5432/gantry
```

```bash
# Install driver
pip install psycopg2-binary
```

#### 3. Migrate Data

```bash
# Export SQLite
sqlite3 data/gantry.db .dump > gantry.sql

# Import to PostgreSQL (manual conversion needed)
# Or use tool like pgloader
```

#### 4. PostgreSQL Tuning

```sql
-- postgresql.conf
shared_buffers = 256MB           -- 25% of RAM
effective_cache_size = 1GB       -- 50% of RAM
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1           -- SSD
effective_io_concurrency = 200   -- SSD
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
max_connections = 200
```

---

## Caching Strategies

### 1. Response Caching

Cache common API responses:

```python
# backend/dependencies.py
from functools import lru_cache
from datetime import datetime, timedelta

# In-memory cache
_cache = {}

def cached_response(key: str, ttl_seconds: int = 60):
    """Simple in-memory cache decorator."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            now = datetime.now()

            # Check cache
            if key in _cache:
                cached_value, expiry = _cache[key]
                if now < expiry:
                    return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            _cache[key] = (result, now + timedelta(seconds=ttl_seconds))

            return result
        return wrapper
    return decorator

# Usage
@router.get("/models")
@cached_response("models_list", ttl_seconds=300)
async def list_models():
    # Expensive operation
    return await model_service.list_models()
```

### 2. Redis Caching

For distributed caching:

```bash
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    container_name: gantry-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - nebulus

volumes:
  redis-data:
```

```python
# backend/cache.py
import redis.asyncio as redis
import json
from typing import Any, Optional

class RedisCache:
    def __init__(self, url: str = "redis://redis:6379"):
        self.redis = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        await self.redis.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str):
        await self.redis.delete(key)

# Usage in routes
from backend.cache import RedisCache

cache = RedisCache()

@router.get("/models")
async def list_models():
    # Try cache first
    cached = await cache.get("models_list")
    if cached:
        return cached

    # Fetch from service
    models = await model_service.list_models()

    # Cache for 5 minutes
    await cache.set("models_list", models, ttl=300)

    return models
```

### 3. Static Asset Caching

Configure in reverse proxy (see [Reverse Proxy Setup](Reverse-Proxy-Setup)):

```nginx
# Nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 4. Browser Caching

```python
# backend/main.py
from fastapi.responses import Response

@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)

    # Cache static assets
    if request.url.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

    return response
```

---

## Backend Scaling

### 1. Horizontal Scaling (Multiple Instances)

Run multiple backend workers:

```yaml
# docker-compose.yml
services:
  backend:
    # ... existing config
    deploy:
      replicas: 3  # Run 3 instances
```

Or manually:

```bash
docker compose up -d --scale backend=3
```

Configure load balancer (Nginx):

```nginx
upstream gantry_backend {
    least_conn;
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
}

location /api/ {
    proxy_pass http://gantry_backend/;
}
```

### 2. Vertical Scaling (More Resources)

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
```

### 3. Async Workers

Already using `async/await` - ensure all I/O operations are async:

```python
# Good - async
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return response.json()

# Bad - blocking
def fetch_data():
    response = requests.get(url)  # Blocks event loop!
    return response.json()
```

### 4. Background Tasks

Offload heavy operations:

```python
# backend/routers/documents.py
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Save file immediately
    doc = save_document(file)

    # Process in background
    background_tasks.add_task(process_document, doc.id, db)

    return {"id": doc.id, "status": "processing"}

async def process_document(doc_id: int, db: Session):
    # Heavy operation: chunking, embedding, indexing
    # Doesn't block the response
    pass
```

### 5. Celery Task Queue

For complex background jobs:

```bash
pip install celery redis
```

```python
# backend/celery_app.py
from celery import Celery

celery_app = Celery(
    "gantry",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1"
)

@celery_app.task
def process_document(doc_id: int):
    # Heavy processing
    pass

# Usage in routes
from backend.celery_app import process_document

@router.post("/upload")
async def upload_document(file: UploadFile):
    doc = save_document(file)
    process_document.delay(doc.id)  # Async execution
    return {"id": doc.id, "status": "processing"}
```

---

## ChromaDB Optimization

### 1. Connection Pooling

```python
# backend/services/memory_service.py
import httpx

class MemoryService:
    def __init__(self):
        # Reuse HTTP client for connection pooling
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20
            )
        )

        self.chroma_client = chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            # Use persistent client
        )
```

### 2. Batch Operations

```python
# Bad - individual inserts
for message in messages:
    memory_service.store(message)

# Good - batch insert
memory_service.store_batch(messages)
```

```python
# backend/services/memory_service.py
def store_batch(self, messages: List[Message]):
    """Store multiple messages at once."""
    collection = self.get_collection("conversations")

    collection.add(
        ids=[str(msg.id) for msg in messages],
        documents=[msg.content for msg in messages],
        metadatas=[{
            "user_id": msg.user_id,
            "conversation_id": msg.conversation_id,
            "role": msg.role,
        } for msg in messages]
    )
```

### 3. Optimize Vector Dimensions

Reduce embedding dimensions for faster search:

```python
# Use smaller embedding model
# Instead of: text-embedding-ada-002 (1536 dims)
# Use: all-MiniLM-L6-v2 (384 dims)

from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(texts)
```

### 4. Collection Sharding

Split large collections:

```python
def get_collection_name(user_id: int) -> str:
    """Shard collections by user."""
    shard = user_id % 10  # 10 shards
    return f"conversations_shard_{shard}"

# Store in appropriate shard
collection = chroma_client.get_or_create_collection(
    name=get_collection_name(user_id)
)
```

### 5. Persistent Storage

```yaml
# docker-compose.yml
services:
  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chromadb-data:/chroma/chroma  # Persistent volume
    environment:
      - CHROMA_SERVER_AUTHN_CREDENTIALS_PROVIDER=token
      - CHROMA_SERVER_AUTHN_TOKEN=your-secure-token
```

---

## LLM Optimization

### 1. Request Batching

Batch multiple chat requests (if your LLM backend supports it):

```python
# Process multiple requests in parallel
import asyncio

async def process_batch(requests: List[ChatRequest]):
    tasks = [llm_service.generate(req) for req in requests]
    responses = await asyncio.gather(*tasks)
    return responses
```

### 2. Streaming Optimization

Already implemented - ensure chunked transfer encoding:

```python
# backend/routers/chat.py
@router.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        generate_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        }
    )
```

### 3. Context Window Management

Limit context size to reduce latency:

```python
def prepare_context(messages: List[Message], max_tokens: int = 4000):
    """Truncate context to fit within limits."""
    context = []
    token_count = 0

    # Start from most recent messages
    for msg in reversed(messages):
        msg_tokens = len(msg.content.split()) * 1.3  # Rough estimate
        if token_count + msg_tokens > max_tokens:
            break
        context.insert(0, msg)
        token_count += msg_tokens

    return context
```

### 4. Model Caching

Cache model responses for identical prompts (use with caution):

```python
import hashlib

def get_cache_key(messages: List[Message]) -> str:
    """Generate cache key from message history."""
    content = "".join([m.content for m in messages])
    return hashlib.sha256(content.encode()).hexdigest()

async def get_response(messages: List[Message]):
    cache_key = get_cache_key(messages)

    # Check cache
    cached = await redis.get(f"llm_response:{cache_key}")
    if cached:
        return cached

    # Generate response
    response = await llm_service.generate(messages)

    # Cache for 1 hour
    await redis.set(f"llm_response:{cache_key}", response, ex=3600)

    return response
```

---

## Frontend Optimization

### 1. Code Splitting

Already configured in Vite:

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@headlessui/react'],
          stores: ['zustand'],
        }
      }
    }
  }
})
```

### 2. Lazy Loading

```typescript
// frontend/src/App.tsx
import { lazy, Suspense } from 'react';

// Lazy load routes
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const KnowledgeVault = lazy(() => import('./pages/KnowledgeVault'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/vault" element={<KnowledgeVault />} />
      </Routes>
    </Suspense>
  );
}
```

### 3. Virtual Scrolling

For long message lists:

```bash
npm install @tanstack/react-virtual
```

```typescript
// frontend/src/components/MessageList.tsx
import { useVirtualizer } from '@tanstack/react-virtual';

function MessageList({ messages }: { messages: Message[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map((item) => (
          <div key={item.key} data-index={item.index}>
            <MessageComponent message={messages[item.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 4. Debounce User Input

```typescript
// frontend/src/hooks/useDebounce.ts
import { useState, useEffect } from 'react';

export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

// Usage
const [searchTerm, setSearchTerm] = useState('');
const debouncedSearch = useDebounce(searchTerm, 300);

useEffect(() => {
  // Only search after user stops typing
  performSearch(debouncedSearch);
}, [debouncedSearch]);
```

### 5. Memoization

```typescript
// frontend/src/components/ChatMessage.tsx
import { memo } from 'react';

const ChatMessage = memo(({ message }: { message: Message }) => {
  // Component only re-renders if message changes
  return <div>{message.content}</div>;
});

// Usage in parent
{messages.map(msg => (
  <ChatMessage key={msg.id} message={msg} />
))}
```

---

## Load Balancing

### Application Layer

Using Docker Swarm:

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml gantry

# Scale services
docker service scale gantry_backend=3
```

### Database Layer

Use read replicas for PostgreSQL:

```python
# backend/database.py
from sqlalchemy import create_engine

# Primary (write)
write_engine = create_engine(DATABASE_WRITE_URL)

# Replicas (read)
read_engine = create_engine(DATABASE_READ_URL)

# Route queries
def get_read_session():
    return Session(bind=read_engine)

def get_write_session():
    return Session(bind=write_engine)
```

---

## Monitoring Performance

### 1. Application Metrics

```python
# backend/middleware.py
import time
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Duration: {duration:.3f}s"
        )

        return response

# Add to app
app.add_middleware(MetricsMiddleware)
```

### 2. Database Query Monitoring

```python
# backend/database.py
from sqlalchemy import event
import logging

logger = logging.getLogger(__name__)

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    logger.info(f"Query: {statement[:100]}... Duration: {total:.3f}s")
```

### 3. Performance Testing

```bash
# Install locust
pip install locust
```

```python
# tests/load_test.py
from locust import HttpUser, task, between

class GantryUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        self.session_id = response.cookies.get("session_id")

    @task(3)
    def list_conversations(self):
        self.client.get("/api/conversations")

    @task(1)
    def send_message(self):
        self.client.post("/api/chat", json={
            "conversation_id": 1,
            "content": "Hello, world!"
        })
```

```bash
# Run load test
locust -f tests/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10
```

---

## Cost Optimization

### 1. Resource Right-Sizing

Monitor actual usage:

```bash
# Docker stats
docker stats --no-stream

# Adjust container limits
docker update --cpus="2.0" --memory="4g" gantry-backend
```

### 2. Storage Optimization

```bash
# Clean up old logs
docker exec gantry-backend find /var/log -name "*.log" -mtime +30 -delete

# Vacuum SQLite
sqlite3 data/gantry.db "VACUUM;"

# Clean Docker
docker system prune -af --volumes
```

### 3. Compression

Enable gzip in reverse proxy - saves bandwidth.

---

## Scalability Checklist

- [ ] Database indexes added
- [ ] Connection pooling configured
- [ ] Caching layer implemented
- [ ] Background tasks for heavy operations
- [ ] Horizontal scaling tested
- [ ] Load balancer configured
- [ ] CDN for static assets
- [ ] Query optimization applied
- [ ] Monitoring and metrics enabled
- [ ] Load testing performed
- [ ] Resource limits tuned

---

## Next Steps

- **[Architecture](Architecture)** - Understand system design
- **[Monitoring](Debugging-Guide)** - Set up observability
- **[Production Checklist](Production-Checklist)** - Security hardening

---

**[← Back to Reverse Proxy Setup](Reverse-Proxy-Setup)** | **[Next: Architecture →](Architecture)**
