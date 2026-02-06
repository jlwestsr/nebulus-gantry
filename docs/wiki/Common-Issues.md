# Common Issues

Frequently asked questions and solutions for typical problems encountered with Nebulus Gantry.

---

## Installation & Setup

### Docker Compose Fails to Start

**Symptom:** `docker compose up` fails with network errors.

**Solution:**

```bash
# Create the external network
docker network create nebulus-prime_ai-network

# Or modify docker-compose.yml to use a different network
networks:
  nebulus:
    external: false  # Create network automatically
```

### Port Already in Use

**Symptom:** `Error: bind: address already in use`

**Solution:**

```bash
# Find what's using the port
sudo lsof -i :8000  # Backend port
sudo lsof -i :3001  # Frontend port

# Kill the process
kill -9 <PID>

# Or change ports in docker-compose.yml
services:
  backend:
    ports:
      - "8001:8000"  # Changed host port
  frontend:
    ports:
      - "3002:3000"  # Changed host port
```

### Database Permission Denied

**Symptom:** `Permission denied: ./data/gantry.db`

**Solution:**

```bash
# Create data directory with correct permissions
mkdir -p data
chmod 777 data  # Development only

# For production, use proper ownership
sudo chown -R 1000:1000 data
```

### Python Virtual Environment Not Activating

**Symptom:** `command not found: python3`

**Solution:**

```bash
# Ensure Python is installed
python3 --version

# Create venv
python3 -m venv backend/venv

# Activate (Linux/macOS)
source backend/venv/bin/activate

# Activate (Windows)
backend\venv\Scripts\activate

# If still failing, install venv module
sudo apt install python3-venv  # Ubuntu/Debian
```

---

## Authentication

### Cannot Login - Invalid Credentials

**Symptom:** Login fails with "Invalid credentials" for correct password.

**Causes & Solutions:**

1. **User doesn't exist**

   ```bash
   # Check if user exists
   docker compose exec backend python -c "
   from backend.database import get_engine, get_session_maker
   from backend.models.user import User
   engine = get_engine()
   Session = get_session_maker(engine)
   db = Session()
   users = db.query(User).all()
   for u in users:
       print(f'{u.id}: {u.email} ({u.role})')
   "
   ```

2. **Database recreated** - User data lost if using `:memory:` or deleted db file

   ```bash
   # Use persistent database
   DATABASE_URL=sqlite:///./data/gantry.db
   ```

3. **Password changed** - Recreate user

   ```bash
   docker compose exec backend python -c "
   from backend.services.auth_service import AuthService
   from backend.database import get_engine, get_session_maker
   engine = get_engine()
   Session = get_session_maker(engine)
   db = Session()
   auth = AuthService(db)
   # Update password
   user = db.query(User).filter(User.email=='admin@example.com').first()
   from backend.services.auth_service import hash_password
   user.password_hash = hash_password('new-password')
   db.commit()
   "
   ```

### Session Expired Immediately

**Symptom:** Login successful but immediately logged out.

**Causes:**

1. **Cookie not being set**

   - Check browser console for cookie errors
   - Verify CORS settings allow credentials
   - Check `credentials: 'include'` in fetch requests

2. **Incorrect API URL**

   ```bash
   # Frontend .env
   VITE_API_URL=http://localhost:8000  # Must match backend
   ```

3. **Session timeout too short**

   ```bash
   # Backend .env
   SESSION_EXPIRE_HOURS=24  # Increase if too short
   ```

### CORS Errors on Login

**Symptom:** `Access-Control-Allow-Origin` error in browser console.

**Solution:**

```python
# backend/main.py - Add frontend URL to allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3001",  # Docker frontend
        "http://localhost:3000",  # Alternative
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Chat & LLM

### LLM Connection Failed

**Symptom:** Chat fails with "Failed to connect to LLM" error.

**Solutions:**

1. **Verify LLM service is running**

   ```bash
   # Test endpoint
   curl http://localhost:5000/v1/models

   # Check TabbyAPI logs
   docker logs tabbyapi  # If using Docker
   ```

2. **Check TABBY_HOST configuration**

   ```bash
   # Backend .env
   TABBY_HOST=http://localhost:5000  # Local
   TABBY_HOST=http://tabbyapi:5000  # Docker network
   ```

3. **Network connectivity**

   ```bash
   # Ping from backend container
   docker compose exec backend curl http://tabbyapi:5000/health
   ```

### Chat Responses are Slow

**Causes & Solutions:**

1. **Large context window**

   - Reduce max_tokens in LLM settings
   - Limit conversation history sent to LLM

2. **Model is slow**

   - Switch to smaller/faster model
   - Increase LLM inference hardware

3. **Network latency**

   - Move LLM service closer to backend
   - Use local deployment instead of remote

### Streaming Not Working

**Symptom:** Full response appears at once instead of streaming.

**Solutions:**

1. **Proxy buffering enabled**

   ```nginx
   # Nginx - Disable buffering
   location /api/chat/stream {
       proxy_buffering off;
       proxy_cache off;
       # ...
   }
   ```

2. **Frontend not using EventSource**

   ```typescript
   // Correct approach
   const eventSource = new EventSource('/api/chat/stream/1', {
     withCredentials: true
   });

   eventSource.onmessage = (event) => {
     const data = JSON.parse(event.data);
     // Handle token
   };
   ```

---

## Memory & ChromaDB

### ChromaDB Connection Failed

**Symptom:** `ChromaDB unavailable` in logs.

**Solutions:**

1. **ChromaDB not running**

   ```bash
   # Start ChromaDB
   docker run -d -p 8001:8000 chromadb/chroma:latest
   ```

2. **Wrong host configuration**

   ```bash
   # Backend .env
   CHROMA_HOST=http://localhost:8001  # From host
   CHROMA_HOST=http://chromadb:8000   # From Docker network
   ```

3. **ChromaDB is optional** - Gantry works without memory features

   ```bash
   # Remove ChromaDB dependency (disables long-term memory)
   CHROMA_HOST=  # Leave empty
   ```

### Memory Search Returns No Results

**Causes:**

1. **No conversations indexed yet**

   - Memory is populated as you chat
   - Wait until you have several conversations

2. **ChromaDB collection empty**

   ```bash
   # Check collections
   curl http://localhost:8001/api/v1/collections
   ```

3. **Embeddings not generated**

   - Check backend logs for embedding errors
   - Verify embedding model is accessible

---

## Documents & Knowledge Vault

### Document Upload Fails

**Symptom:** Upload returns error or document status stuck on "processing".

**Solutions:**

1. **File too large**

   ```python
   # Increase max upload size in backend/main.py
   from fastapi.middleware.cors import CORSMiddleware
   from starlette.middleware import Middleware
   from starlette.middleware.base import BaseHTTPMiddleware

   # Add size limit
   app.add_middleware(
       # Configure max body size
   )
   ```

2. **Unsupported file type**

   - Supported: PDF, DOCX, TXT, CSV
   - Convert other formats before uploading

3. **Disk space full**

   ```bash
   # Check disk space
   df -h

   # Clean up old files
   docker system prune -a
   ```

### Document Not Appearing in RAG Results

**Causes:**

1. **Document still processing**

   - Check document status via API
   - Processing can take minutes for large PDFs

2. **Wrong collection**

   - Ensure document and query use same collection
   - Check collection name matches exactly

3. **Query doesn't match content**

   - Try different search terms
   - Check document was parsed correctly

---

## Frontend Issues

### White Screen on Load

**Symptom:** Frontend shows blank white screen.

**Solutions:**

1. **Check browser console for errors**

   - Press F12 to open DevTools
   - Look for JavaScript errors

2. **API URL misconfigured**

   ```bash
   # Frontend .env
   VITE_API_URL=http://localhost:8000

   # Rebuild frontend
   docker compose up -d --build frontend
   ```

3. **Build failed**

   ```bash
   # Check frontend logs
   docker compose logs frontend

   # Rebuild manually
   cd frontend
   npm install
   npm run build
   ```

### UI Not Updating After Changes

**Symptom:** Code changes don't appear in browser.

**Solutions:**

1. **Hot reload not working**

   ```bash
   # Restart dev server
   npm run dev
   ```

2. **Browser cache**

   - Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (macOS)
   - Clear browser cache

3. **Build artifacts stale**

   ```bash
   # Clean and rebuild
   rm -rf frontend/dist frontend/node_modules/.vite
   npm run build
   ```

---

## Database Issues

### Database is Locked

**Symptom:** `database is locked` error.

**Solutions:**

1. **Multiple processes accessing SQLite**

   ```bash
   # Stop all processes
   docker compose down

   # Enable WAL mode for better concurrency
   sqlite3 data/gantry.db "PRAGMA journal_mode=WAL;"
   ```

2. **Switch to PostgreSQL for production**

   ```bash
   # PostgreSQL handles concurrency better
   DATABASE_URL=postgresql://user:pass@host:5432/gantry
   ```

### Database Migrations Not Applied

**Symptom:** `Table doesn't exist` errors.

**Solutions:**

```bash
# Recreate database schema
docker compose exec backend python -c "
from backend.database import get_engine, Base
from backend.models import *
engine = get_engine()
Base.metadata.create_all(bind=engine)
"

# Or delete and recreate
rm data/gantry.db
docker compose restart backend
```

---

## Performance Issues

### High Memory Usage

**Solutions:**

1. **Limit connection pool size**

   ```python
   # backend/database.py
   engine = create_engine(
       DATABASE_URL,
       pool_size=10,  # Reduce from 20
       max_overflow=20,  # Reduce from 40
   )
   ```

2. **Reduce conversation history context**

   - Load fewer messages per request
   - Implement pagination

3. **Monitor with docker stats**

   ```bash
   docker stats
   ```

### Slow Database Queries

**Solutions:**

1. **Add indexes**

   ```python
   # backend/models/message.py
   __table_args__ = (
       Index('idx_conversation_created', 'conversation_id', 'created_at'),
   )
   ```

2. **Use PostgreSQL instead of SQLite**

3. **Optimize queries**

   ```python
   # Bad - N+1 query problem
   for conv in conversations:
       messages = conv.messages  # Separate query per conversation

   # Good - Eager loading
   conversations = db.query(Conversation).options(
       joinedload(Conversation.messages)
   ).all()
   ```

---

## Docker Issues

### Container Keeps Restarting

**Symptom:** `docker compose ps` shows container restarting continuously.

**Solutions:**

```bash
# Check logs for error
docker compose logs backend

# Common causes:
# 1. Missing environment variable
# 2. Database connection failed
# 3. Port conflict
# 4. Syntax error in code
```

### Cannot Remove Container

**Symptom:** `Error response from daemon: conflict: unable to remove`

**Solutions:**

```bash
# Force remove
docker rm -f container_name

# Remove all stopped containers
docker container prune
```

### Image Build Fails

**Solutions:**

```bash
# Clear build cache
docker builder prune -a

# Rebuild without cache
docker compose build --no-cache

# Check Dockerfile syntax
docker compose config
```

---

## Admin Dashboard

### Cannot Access Admin Panel

**Symptom:** 403 Forbidden when accessing `/admin`.

**Cause:** User account is not admin role.

**Solution:**

```bash
# Promote user to admin
docker compose exec backend python -c "
from backend.database import get_engine, get_session_maker
from backend.models.user import User
engine = get_engine()
Session = get_session_maker(engine)
db = Session()
user = db.query(User).filter(User.email=='user@example.com').first()
user.role = 'admin'
db.commit()
print(f'{user.email} is now admin')
"
```

### Model Switching Not Working

**Symptom:** Model list empty or switch fails.

**Causes:**

1. **Not using TabbyAPI**

   - Model switching requires TabbyAPI backend
   - Not supported with Ollama, vLLM, etc.

2. **TabbyAPI not exposing model list**

   ```bash
   # Test TabbyAPI endpoint
   curl http://localhost:5000/v1/models
   ```

---

## Environment Configuration

### Environment Variables Not Loading

**Solutions:**

1. **Check .env file location**

   ```bash
   # .env must be in same directory as docker-compose.yml
   ls -la .env
   ```

2. **Restart services after changing .env**

   ```bash
   docker compose down
   docker compose up -d
   ```

3. **Verify variables are set**

   ```bash
   docker compose exec backend env | grep DATABASE_URL
   ```

### Production vs Development Config

**Setup:**

```bash
# Development
.env.development

# Production
.env.production

# Load specific env file
docker compose --env-file .env.production up -d
```

---

## Testing

### Tests Failing Locally

**Solutions:**

1. **Dependencies out of date**

   ```bash
   pip install -r requirements.txt --upgrade
   npm install
   ```

2. **Test database conflict**

   ```bash
   # Tests should use in-memory database
   # Check conftest.py uses sqlite:///:memory:
   ```

3. **Run tests in isolation**

   ```bash
   pytest --no-cov -x  # Stop on first failure
   pytest -k test_name  # Run specific test
   ```

---

## Logs & Debugging

### Where to Find Logs

```bash
# Docker logs
docker compose logs -f backend
docker compose logs -f frontend

# Backend logs (manual setup)
tail -f backend/logs/app.log

# Frontend browser console
# Press F12 > Console tab
```

### Enable Debug Logging

```bash
# Backend .env
LOG_LEVEL=DEBUG

# Restart services
docker compose restart
```

### Common Log Messages

**"ChromaDB unavailable"** - Memory service degraded, not critical

**"Failed to connect to LLM"** - Check TABBY_HOST and LLM service

**"Session expired"** - Normal, user needs to re-login

**"Database is locked"** - SQLite concurrency issue, see above

---

## Getting More Help

If your issue isn't covered here:

1. **Search GitHub Issues** - Someone may have had the same problem
2. **Check Debugging Guide** - More detailed troubleshooting steps
3. **Ask in Discussions** - Community Q&A
4. **Open an Issue** - Report bugs with logs and steps to reproduce

---

## Related Documentation

- **[Installation Guide](Installation)** - Setup instructions
- **[Configuration](Configuration)** - Environment variable reference
- **[Debugging Guide](Debugging-Guide)** - Advanced troubleshooting
- **[Development Setup](Development-Setup)** - Local development help

---

**[← Back to Contributing](Contributing)** | **[Next: Debugging Guide →](Debugging-Guide)**
