# Debugging Guide

Comprehensive guide for diagnosing and resolving issues in Nebulus Gantry, including log analysis, error diagnosis, and troubleshooting tools.

---

## Log Access

### Docker Logs

```bash
# View all logs
docker compose logs

# Follow logs in real-time
docker compose logs -f

# Specific service
docker compose logs backend
docker compose logs frontend

# Last N lines
docker compose logs --tail=100 backend

# With timestamps
docker compose logs -t backend

# Filter by time
docker compose logs --since 30m backend
docker compose logs --until 2h backend
```

### Backend Logs

```bash
# Running in Docker
docker compose logs -f backend | grep ERROR

# Manual deployment
tail -f backend/logs/app.log

# Filter by log level
grep "ERROR" backend/logs/app.log
grep "WARNING" backend/logs/app.log
```

### Frontend Logs

```bash
# Docker container logs
docker compose logs -f frontend

# Browser console (F12)
# Check Console tab for errors

# Network requests (F12)
# Check Network tab for failed requests
```

---

## Log Levels

### Understanding Log Levels

| Level | Severity | When to Use |
|-------|----------|-------------|
| `DEBUG` | Lowest | Development, detailed tracing |
| `INFO` | Normal | Standard operations |
| `WARNING` | Moderate | Recoverable issues |
| `ERROR` | High | Operation failures |
| `CRITICAL` | Highest | System failures |

### Configuring Log Levels

```bash
# Backend .env
LOG_LEVEL=DEBUG  # Development
LOG_LEVEL=INFO   # Production
LOG_LEVEL=ERROR  # Only errors
```

---

## Common Error Patterns

### Backend Errors

#### Database Errors

**Pattern:** `sqlalchemy.exc.OperationalError: database is locked`

**Diagnosis:**

```bash
# Check who's accessing database
lsof data/gantry.db

# Check database mode
sqlite3 data/gantry.db "PRAGMA journal_mode;"
```

**Solution:**

```bash
# Enable WAL mode
sqlite3 data/gantry.db "PRAGMA journal_mode=WAL;"

# Or switch to PostgreSQL
DATABASE_URL=postgresql://user:pass@host:5432/gantry
```

#### Connection Errors

**Pattern:** `httpx.ConnectError: [Errno 111] Connection refused`

**Diagnosis:**

```bash
# Test service connectivity
curl http://localhost:5000/health  # LLM
curl http://localhost:8001/api/v1/heartbeat  # ChromaDB

# Check service is running
docker ps | grep tabbyapi
docker ps | grep chromadb
```

**Solution:**

```bash
# Start missing service
docker run -d -p 5000:5000 tabbyapi

# Verify network connectivity
docker compose exec backend ping chromadb
```

#### Import Errors

**Pattern:** `ModuleNotFoundError: No module named 'package'`

**Diagnosis:**

```bash
# Check installed packages
docker compose exec backend pip list

# Verify requirements.txt
cat backend/requirements.txt
```

**Solution:**

```bash
# Reinstall dependencies
docker compose exec backend pip install -r requirements.txt

# Or rebuild container
docker compose up -d --build backend
```

#### Authentication Errors

**Pattern:** `401 Unauthorized` or `Session expired`

**Diagnosis:**

```bash
# Check session in database
docker compose exec backend python -c "
from backend.database import get_engine, get_session_maker
from backend.models.session import Session
engine = get_engine()
SessionMaker = get_session_maker(engine)
db = SessionMaker()
sessions = db.query(Session).all()
for s in sessions:
    print(f'{s.id}: user={s.user_id} expires={s.expires_at}')
"
```

**Solution:**

```bash
# Increase session timeout
SESSION_EXPIRE_HOURS=24  # .env

# Clear expired sessions
docker compose exec backend python -c "
from backend.database import get_engine, get_session_maker
from backend.models.session import Session
from datetime import datetime
engine = get_engine()
SessionMaker = get_session_maker(engine)
db = SessionMaker()
db.query(Session).filter(Session.expires_at < datetime.now()).delete()
db.commit()
"
```

### Frontend Errors

#### Network Errors

**Pattern:** `Failed to fetch` or `NetworkError`

**Diagnosis:**

```bash
# Check API URL
echo $VITE_API_URL

# Test backend connectivity
curl http://localhost:8000/health

# Check CORS headers
curl -I -X OPTIONS http://localhost:8000/api/auth/login
```

**Solution:**

```bash
# Fix API URL in frontend .env
VITE_API_URL=http://localhost:8000

# Rebuild frontend
docker compose up -d --build frontend
```

#### CORS Errors

**Pattern:** `Access-Control-Allow-Origin` error in console

**Diagnosis:**

Check backend CORS configuration in `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Must include frontend URL
    allow_credentials=True,
)
```

**Solution:**

```python
# Add all frontend URLs
allow_origins=[
    "http://localhost:5173",  # Vite dev
    "http://localhost:3001",  # Docker
    "http://localhost:3000",  # Alternative
]
```

#### State Management Issues

**Pattern:** UI not updating, stale data

**Diagnosis:**

```javascript
// Add debug logging to stores
export const useChatStore = create((set) => ({
  messages: [],
  addMessage: (msg) => {
    console.log('Adding message:', msg);
    set((state) => {
      console.log('Previous state:', state.messages);
      return { messages: [...state.messages, msg] };
    });
  },
}));
```

---

## Debugging Tools

### Backend Debugging

#### Python Debugger (pdb)

```python
# Add breakpoint in code
def process_message(message):
    import pdb; pdb.set_trace()  # Execution stops here
    result = expensive_operation(message)
    return result

# Or use built-in breakpoint()
def process_message(message):
    breakpoint()  # Python 3.7+
    result = expensive_operation(message)
    return result
```

**pdb Commands:**

```text
n       - Next line
s       - Step into function
c       - Continue execution
l       - List code around current line
p var   - Print variable
pp var  - Pretty print variable
q       - Quit debugger
h       - Help
```

#### Interactive Python Shell

```bash
# Access Python shell in container
docker compose exec backend python

# Or with iPython (better)
docker compose exec backend ipython

# Load app context
>>> from backend.main import app
>>> from backend.database import get_engine, get_session_maker
>>> engine = get_engine()
>>> Session = get_session_maker(engine)
>>> db = Session()

# Query database
>>> from backend.models.user import User
>>> users = db.query(User).all()
>>> for u in users:
...     print(f"{u.email}: {u.role}")
```

#### Request Logging

```python
# backend/main.py
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        logger.info(f"Headers: {dict(request.headers)}")

        response = await call_next(request)

        logger.info(f"Response: {response.status_code}")
        return response

app.add_middleware(LoggingMiddleware)
```

#### SQL Query Logging

```python
# backend/database.py
import logging

# Enable SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# See all queries in logs
# Example output:
# INFO sqlalchemy.engine.Engine SELECT user.id, user.email FROM user
# INFO sqlalchemy.engine.Engine ()
```

### Frontend Debugging

#### React DevTools

Install browser extension:

- [Chrome](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/react-devtools/)

**Features:**

- Inspect component tree
- View props and state
- Profile performance
- Track re-renders

#### Redux DevTools (for Zustand)

```typescript
// stores/chatStore.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export const useChatStore = create(
  devtools(
    (set) => ({
      messages: [],
      addMessage: (msg) => set((state) => ({
        messages: [...state.messages, msg]
      })),
    }),
    { name: 'ChatStore' }  // Shows in Redux DevTools
  )
);
```

#### Network Debugging

**Browser DevTools > Network tab:**

1. Record network activity
2. Filter by XHR/Fetch
3. Inspect request/response headers
4. View request payload
5. Check response status and body

**Chrome Network Conditions:**

- Throttle network speed
- Disable cache
- Offline mode testing

#### Console Debugging

```typescript
// Add strategic console logs
console.log('User data:', user);
console.table(messages);  // Table format
console.group('Chat Operations');
console.log('Sending message...');
console.log('Response received');
console.groupEnd();

// Measure performance
console.time('API call');
await api.sendMessage(data);
console.timeEnd('API call');  // Outputs duration
```

---

## Performance Profiling

### Backend Profiling

#### cProfile

```bash
# Profile specific script
python -m cProfile -o output.prof backend/main.py

# Analyze results
python -m pstats output.prof
>>> sort cumulative
>>> stats 10  # Top 10 slowest functions
```

#### Line Profiler

```bash
# Install
pip install line_profiler

# Decorate function
from line_profiler import profile

@profile
def slow_function():
    # Code to profile
    pass

# Run
kernprof -l -v script.py
```

#### Request Timing

```python
# backend/main.py
import time
from starlette.middleware.base import BaseHTTPMiddleware

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            f"{request.method} {request.url.path} "
            f"completed in {duration:.3f}s"
        )

        response.headers["X-Process-Time"] = str(duration)
        return response

app.add_middleware(TimingMiddleware)
```

### Frontend Profiling

#### React Profiler

```typescript
import { Profiler } from 'react';

function onRenderCallback(
  id: string,
  phase: 'mount' | 'update',
  actualDuration: number,
  baseDuration: number,
  startTime: number,
  commitTime: number
) {
  console.log(`${id} (${phase}): ${actualDuration}ms`);
}

function App() {
  return (
    <Profiler id="App" onRender={onRenderCallback}>
      <YourComponent />
    </Profiler>
  );
}
```

#### Performance API

```typescript
// Measure operation timing
const start = performance.now();
await expensiveOperation();
const end = performance.now();
console.log(`Operation took ${end - start}ms`);

// Mark specific events
performance.mark('message-send-start');
await api.sendMessage(data);
performance.mark('message-send-end');

performance.measure(
  'message-send',
  'message-send-start',
  'message-send-end'
);

const measure = performance.getEntriesByName('message-send')[0];
console.log(`Message send: ${measure.duration}ms`);
```

---

## Database Debugging

### Query Analysis

```bash
# SQLite query plan
sqlite3 data/gantry.db "EXPLAIN QUERY PLAN SELECT * FROM messages WHERE conversation_id = 1;"

# Find slow queries
# Enable query logging first (see above)
grep "SELECT" backend/logs/app.log | sort -k4 -rn | head -10
```

### Database Inspection

```bash
# Open database shell
sqlite3 data/gantry.db

# List tables
.tables

# Show schema
.schema users
.schema messages

# Query data
SELECT * FROM users;
SELECT COUNT(*) FROM messages;
SELECT conversation_id, COUNT(*) FROM messages GROUP BY conversation_id;

# Export data
.mode csv
.output backup.csv
SELECT * FROM messages;
.output stdout
```

### Index Usage

```sql
-- Check indexes
SELECT name, sql FROM sqlite_master WHERE type='index';

-- Add missing indexes
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at);

-- Analyze index usage
ANALYZE;
```

---

## Memory Debugging

### Monitor Memory Usage

```bash
# Docker stats
docker stats --no-stream

# Detailed container info
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Process memory (inside container)
docker compose exec backend ps aux --sort=-%mem | head -10
```

### Python Memory Profiling

```bash
# Install memory_profiler
pip install memory_profiler

# Decorate function
from memory_profiler import profile

@profile
def memory_intensive_function():
    large_list = [i for i in range(1000000)]
    return large_list

# Run
python -m memory_profiler script.py
```

### Memory Leaks

```python
# Check object counts
import gc

# Force garbage collection
gc.collect()

# Count objects by type
from collections import Counter
counter = Counter()
for obj in gc.get_objects():
    counter[type(obj).__name__] += 1

# Print top 10
for obj_type, count in counter.most_common(10):
    print(f"{obj_type}: {count}")
```

---

## Error Tracking

### Sentry Integration

```bash
# Install
pip install sentry-sdk[fastapi]
```

```python
# backend/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    environment="production",
    traces_sample_rate=0.1,
    integrations=[FastApiIntegration()],
)

# Errors automatically tracked
# Add custom context
with sentry_sdk.configure_scope() as scope:
    scope.set_user({"id": user.id, "email": user.email})
    scope.set_tag("conversation_id", conv_id)
```

### Custom Error Logging

```python
# backend/utils/error_handler.py
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

def log_error(error: Exception, context: dict = None):
    """Log error with full context."""
    error_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context or {},
    }

    logger.error(json.dumps(error_data, indent=2))

# Usage
try:
    result = risky_operation()
except Exception as e:
    log_error(e, context={
        "user_id": user.id,
        "conversation_id": conv_id,
        "operation": "send_message"
    })
    raise
```

---

## Health Checks

### Endpoint Monitoring

```bash
# Backend health
curl http://localhost:8000/health

# Expected response:
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

### Automated Monitoring

```bash
# Simple monitoring script
#!/bin/bash
# monitor.sh

BACKEND_URL="http://localhost:8000"

while true; do
    response=$(curl -s -o /dev/null -w "%{http_code}" $BACKEND_URL/health)

    if [ $response -eq 200 ]; then
        echo "$(date): Backend healthy"
    else
        echo "$(date): Backend unhealthy (HTTP $response)"
        # Send alert
    fi

    sleep 60
done
```

### Prometheus Metrics

```bash
# Install
pip install prometheus-fastapi-instrumentator
```

```python
# backend/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Add metrics endpoint
Instrumentator().instrument(app).expose(app)

# Metrics available at /metrics
# Use with Prometheus + Grafana
```

---

## Troubleshooting Checklist

When debugging issues, work through this checklist:

### 1. Reproduce the Issue

- [ ] Can you reproduce consistently?
- [ ] What are the exact steps?
- [ ] Does it happen in different environments?

### 2. Check Logs

- [ ] Backend logs reviewed
- [ ] Frontend console checked
- [ ] Any error messages noted

### 3. Verify Configuration

- [ ] Environment variables correct
- [ ] Services running
- [ ] Network connectivity working

### 4. Isolate the Problem

- [ ] Frontend or backend issue?
- [ ] Which specific component?
- [ ] Recent changes that might have caused it?

### 5. Test Components

- [ ] Database accessible
- [ ] LLM service responding
- [ ] ChromaDB connected
- [ ] Authentication working

### 6. Check Resources

- [ ] Disk space available
- [ ] Memory usage normal
- [ ] CPU usage normal
- [ ] Network latency acceptable

### 7. Review Code

- [ ] Recent git changes
- [ ] Dependencies updated
- [ ] Tests passing

---

## Advanced Debugging

### Remote Debugging

```python
# backend/main.py
# Install debugpy
# pip install debugpy

import debugpy

# Listen on port 5678
debugpy.listen(("0.0.0.0", 5678))
print("Waiting for debugger attach...")
# debugpy.wait_for_client()  # Uncomment to block until attached
```

**VS Code launch.json:**

```json
{
  "name": "Remote Backend",
  "type": "python",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 5678
  },
  "pathMappings": [
    {
      "localRoot": "${workspaceFolder}/backend",
      "remoteRoot": "/app"
    }
  ]
}
```

### Packet Capture

```bash
# Capture HTTP traffic
tcpdump -i any -A 'tcp port 8000' -w capture.pcap

# Analyze with Wireshark
wireshark capture.pcap

# Or use tshark
tshark -r capture.pcap -Y http
```

---

## Getting Help

If you're still stuck:

1. **Document your findings**
   - Error messages
   - Logs
   - Steps to reproduce
   - Environment details

2. **Search existing issues**
   - GitHub Issues
   - Discussions

3. **Ask for help**
   - Open new issue with details
   - Ask in Discussions
   - Include relevant logs

---

## Related Documentation

- **[Common Issues](Common-Issues)** - FAQ with quick solutions
- **[Development Setup](Development-Setup)** - Local debugging setup
- **[Testing](Testing)** - Writing tests to catch bugs
- **[Contributing](Contributing)** - Reporting bugs properly

---

**[← Back to Common Issues](Common-Issues)** | **[Home](Home)**
