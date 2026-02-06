# Configuration Guide

Comprehensive guide to configuring Nebulus Gantry through environment variables, settings, and integration options.

---

## Environment Variables

Gantry is configured entirely through environment variables defined in `.env` files.

### Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/gantry.db` | SQLAlchemy database connection string |
| `SECRET_KEY` | `dev-secret-change-in-production` | Session signing secret (MUST change in production!) |
| `TABBY_HOST` | `http://localhost:5000` | LLM API endpoint (OpenAI-compatible) |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROMA_HOST` | `http://localhost:8000` | ChromaDB endpoint for vector storage |
| `SESSION_EXPIRE_HOURS` | `24` | Session cookie lifetime in hours |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL for frontend (build-time only) |

---

## Configuration Files

### Backend Configuration (`.env`)

Create `.env` in the project root:

```bash
# Database
DATABASE_URL=sqlite:///./data/gantry.db

# External Services
CHROMA_HOST=http://chromadb:8000
TABBY_HOST=http://your-llm-api:5000

# Security
SECRET_KEY=your-random-32-character-secret-key
SESSION_EXPIRE_HOURS=24

# Frontend (build-time)
VITE_API_URL=http://localhost:8000
```

### Frontend Configuration

The frontend uses **build-time** environment variables. Changes to `VITE_API_URL` require a rebuild:

```bash
docker compose up -d --build frontend
```

---

## Database Configuration

### SQLite (Default)

**Configuration:**

```bash
DATABASE_URL=sqlite:///./data/gantry.db
```

**Pros:**

- Zero configuration
- File-based (easy backups)
- Perfect for single-server deployments

**Cons:**

- Not suitable for distributed deployments
- Limited concurrent write performance

**Backup:**

```bash
# Backup database
cp data/gantry.db data/gantry.db.backup

# Restore from backup
cp data/gantry.db.backup data/gantry.db
```

### PostgreSQL (Production)

**Configuration:**

```bash
DATABASE_URL=postgresql://username:password@host:5432/gantry
```

**Setup with Docker:**

```yaml
# Add to docker-compose.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: gantry
      POSTGRES_PASSWORD: secure-password
      POSTGRES_DB: gantry
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - nebulus

volumes:
  postgres-data:
```

**Update `.env`:**

```bash
DATABASE_URL=postgresql://gantry:secure-password@postgres:5432/gantry
```

### MySQL/MariaDB

**Configuration:**

```bash
DATABASE_URL=mysql+pymysql://username:password@host:3306/gantry
```

**Additional dependency:**

```bash
pip install pymysql
```

---

## LLM Backend Configuration

Gantry works with any **OpenAI-compatible API**. Configure via `TABBY_HOST`.

### TabbyAPI (Recommended)

**Best integration** with model switching support.

**Setup:**

```bash
# Install TabbyAPI
git clone https://github.com/theroyallab/tabbyAPI.git
cd tabbyAPI
pip install -r requirements.txt

# Download a model (example: Qwen2.5-Coder-7B-Instruct)
# Place in models/ directory

# Start TabbyAPI
python main.py --host 0.0.0.0 --port 5000
```

**Configuration:**

```bash
TABBY_HOST=http://192.168.1.100:5000
```

**Docker network:**

```bash
# If TabbyAPI runs in Docker on same host
TABBY_HOST=http://tabbyapi:5000

# Add to TabbyAPI's docker-compose.yml:
networks:
  default:
    name: nebulus-prime_ai-network
    external: true
```

### Ollama

**Easy installation**, great for macOS.

**Setup:**

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download a model
ollama pull llama3.1:8b

# Ollama runs on port 11434 by default
```

**Configuration:**

```bash
TABBY_HOST=http://192.168.1.100:11434
```

**Note:** Ollama does not support model switching via API (Gantry's model switcher won't work).

### vLLM

**High-performance** production inference server.

**Setup:**

```bash
# Install vLLM
pip install vllm

# Start server with a model
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --host 0.0.0.0 \
  --port 5000
```

**Configuration:**

```bash
TABBY_HOST=http://192.168.1.100:5000
```

### LM Studio

**Desktop GUI** application.

**Setup:**

1. Download from <https://lmstudio.ai/>
2. Load a model in the UI
3. Go to **Developer** tab
4. Click **Start Server** (default port: 1234)

**Configuration:**

```bash
TABBY_HOST=http://192.168.1.100:1234
```

### LocalAI

**All-in-one** local inference with many model formats.

**Setup:**

```bash
docker run -d \
  --name localai \
  -p 5000:8080 \
  -v localai-models:/models \
  localai/localai:latest
```

**Configuration:**

```bash
TABBY_HOST=http://192.168.1.100:5000
```

### OpenAI API (Cloud)

**Not private**, but useful for testing.

**Configuration:**

```bash
TABBY_HOST=https://api.openai.com/v1
```

**Add API key** in `backend/config.py`:

```python
# Add to Settings class
openai_api_key: str = Field(default="")
```

**Update LLM client** in `backend/services/llm_service.py` to pass API key in headers.

---

## ChromaDB Configuration

ChromaDB provides **vector search** for long-term memory and document search (RAG).

### Docker ChromaDB (Recommended)

**Setup:**

```bash
docker run -d \
  --name chromadb \
  --network nebulus-prime_ai-network \
  -p 8001:8000 \
  -v chromadb-data:/chroma/chroma \
  chromadb/chroma:latest
```

**Configuration:**

```bash
# If accessing from Docker network
CHROMA_HOST=http://chromadb:8000

# If accessing from host
CHROMA_HOST=http://localhost:8001
```

**Verify:**

```bash
curl http://localhost:8001/api/v1/heartbeat
# Expected: {"nanosecond heartbeat": ...}
```

### Local ChromaDB

**Setup:**

```bash
pip install chromadb

# Start ChromaDB server
chroma run --host 0.0.0.0 --port 8001
```

**Configuration:**

```bash
CHROMA_HOST=http://localhost:8001
```

### ChromaDB Persistence

ChromaDB data survives container rebuilds when using Docker volumes:

```yaml
# In docker-compose.yml
services:
  chromadb:
    volumes:
      - chromadb-data:/chroma/chroma

volumes:
  chromadb-data:
    external: true
    name: nebulus-prime_chroma_data
```

**Backup ChromaDB:**

```bash
# Backup volume
docker run --rm -v nebulus-prime_chroma_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/chromadb-backup.tar.gz /data

# Restore volume
docker run --rm -v nebulus-prime_chroma_data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/chromadb-backup.tar.gz -C /
```

### Disable ChromaDB

ChromaDB is **optional**. If not available, Gantry works without memory features:

```bash
# Leave CHROMA_HOST empty or pointing to non-existent host
CHROMA_HOST=http://chromadb:8000

# Backend will log: "ChromaDB unavailable - memory features disabled"
```

---

## Security Configuration

### Secret Key

**Critical:** Change `SECRET_KEY` in production!

**Generate a secure key:**

```bash
# Linux/macOS
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

**Example:**

```bash
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345
```

**Used for:**

- Session cookie signing
- CSRF token generation
- Password reset tokens (future feature)

### Session Expiration

Control how long users stay logged in:

```bash
# Default: 24 hours
SESSION_EXPIRE_HOURS=24

# Production: Shorter for security
SESSION_EXPIRE_HOURS=8

# Development: Longer for convenience
SESSION_EXPIRE_HOURS=168  # 1 week
```

### CORS Settings

Configure allowed origins in `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://localhost:5173",
        "https://yourdomain.com",  # Add production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production:** Only allow your domain, not `*`.

---

## Docker Network Configuration

### Default Network

Gantry expects an external network:

```yaml
# docker-compose.yml
networks:
  nebulus:
    external: true
    name: nebulus-prime_ai-network
```

**Create network:**

```bash
docker network create nebulus-prime_ai-network
```

### Custom Network

**Change network name:**

```yaml
networks:
  nebulus:
    external: true
    name: my-custom-network
```

**Update all services:**

```bash
# Update TABBY_HOST and CHROMA_HOST to use new network names
TABBY_HOST=http://tabbyapi:5000
CHROMA_HOST=http://chromadb:8000
```

### Bridge Mode (No External Network)

**Remove external network:**

```yaml
# docker-compose.yml
networks:
  nebulus:
    driver: bridge
```

**Update hosts:**

```bash
# Use host.docker.internal for host services
TABBY_HOST=http://host.docker.internal:5000
CHROMA_HOST=http://host.docker.internal:8001
```

---

## Port Configuration

### Default Ports

| Service | Container | Host | Purpose |
|---------|-----------|------|---------|
| Backend | 8000 | 8000 | FastAPI REST API |
| Frontend | 3000 | 3001 | React dev server |

### Change Ports

**Edit `docker-compose.yml`:**

```yaml
services:
  backend:
    ports:
      - "8080:8000"  # Host:Container

  frontend:
    ports:
      - "3002:3000"
```

**Update `.env`:**

```bash
VITE_API_URL=http://localhost:8080
```

**Rebuild frontend:**

```bash
docker compose up -d --build frontend
```

---

## Storage Configuration

### SQLite Data Directory

**Default location:**

```bash
./data/gantry.db
```

**Change location:**

```bash
DATABASE_URL=sqlite:////absolute/path/to/gantry.db
```

**Docker volume:**

```yaml
services:
  backend:
    volumes:
      - ./data:/app/data  # Host:Container
```

### Document Storage

**Knowledge Vault documents** are stored as:

- **Metadata:** SQLite database (`documents` table)
- **Text chunks:** ChromaDB vectors
- **Original files:** Not stored (only text extracted)

### Log Files

**Backend logs:**

```bash
docker compose logs backend > backend.log
```

**Frontend logs:**

```bash
docker compose logs frontend > frontend.log
```

**Persistent logging** (optional):

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Performance Configuration

### Backend Workers

**Default:** 1 worker (development)

**Production:** Multiple workers

```yaml
# docker-compose.yml
services:
  backend:
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Formula:** `(2 × CPU cores) + 1`

### Database Tuning

**SQLite:**

```python
# backend/database.py
engine = create_engine(
    settings.database_url,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # Seconds to wait for locks
    },
    pool_pre_ping=True,
)
```

**PostgreSQL:**

```bash
DATABASE_URL=postgresql://user:pass@host/db?pool_size=20&max_overflow=10
```

### ChromaDB Performance

**Batch size for embeddings:**

```python
# backend/services/memory_service.py
BATCH_SIZE = 100  # Process 100 chunks at a time
```

**Increase for faster bulk uploads, decrease for lower memory usage.**

---

## Development vs Production

### Development Configuration

```bash
# .env.development
DATABASE_URL=sqlite:///./data/gantry-dev.db
CHROMA_HOST=http://localhost:8001
TABBY_HOST=http://localhost:5000
SECRET_KEY=dev-secret-not-for-production
SESSION_EXPIRE_HOURS=168
VITE_API_URL=http://localhost:8000
```

**Features:**

- Local SQLite
- Long session expiration
- Permissive CORS
- Debug logging

### Production Configuration

```bash
# .env.production
DATABASE_URL=postgresql://gantry:secure-pass@postgres:5432/gantry
CHROMA_HOST=http://chromadb:8000
TABBY_HOST=http://tabbyapi:5000
SECRET_KEY=<generated-with-openssl-rand>
SESSION_EXPIRE_HOURS=8
VITE_API_URL=https://yourdomain.com/api
```

**Features:**

- PostgreSQL for reliability
- Short session expiration
- Strict CORS (single domain)
- Info-level logging
- Multiple backend workers
- HTTPS only

---

## Environment-Specific Overrides

### Multiple `.env` Files

```bash
.env              # Base configuration
.env.local        # Local overrides (gitignored)
.env.production   # Production values
```

**Load order:**

```bash
# Development
docker compose --env-file .env.local up

# Production
docker compose --env-file .env.production up -d
```

### Docker Compose Override

```yaml
# docker-compose.override.yml (auto-loaded in development)
services:
  backend:
    volumes:
      - ./backend:/app/backend  # Live code reload
    command: uvicorn backend.main:app --reload --host 0.0.0.0
```

**Production:** Use `docker-compose.prod.yml` with `--no-reload`.

---

## Verification

### Check Configuration

```bash
# Backend health with config check
curl http://localhost:8000/health

# View loaded config (add debug endpoint)
curl http://localhost:8000/debug/config
```

### Test Connections

```bash
# Test LLM
curl http://your-llm-host:5000/v1/models

# Test ChromaDB
curl http://localhost:8001/api/v1/heartbeat

# Test database
docker compose exec backend python -c "
from backend.database import get_engine
engine = get_engine()
print('Database connected:', engine.url)
"
```

---

## Troubleshooting Configuration

### Changes Not Applying

**Frontend changes:**

```bash
# Frontend uses build-time vars - must rebuild
docker compose up -d --build frontend
```

**Backend changes:**

```bash
# Backend reads .env at startup - restart
docker compose restart backend
```

### Invalid Database URL

**Error:** `Invalid database URL`

**Fix:** Check SQLAlchemy format:

```bash
# SQLite
sqlite:///./data/gantry.db

# PostgreSQL
postgresql://user:pass@host:5432/dbname

# MySQL
mysql+pymysql://user:pass@host:3306/dbname
```

### Secret Key Warning

**Warning:** `Using default SECRET_KEY in production`

**Fix:**

```bash
# Generate new key
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY" >> .env

# Restart
docker compose restart backend
```

---

## Next Steps

- **[Docker Deployment](Docker-Deployment)** - Production Docker setup
- **[Production Checklist](Production-Checklist)** - Security hardening
- **[Reverse Proxy Setup](Reverse-Proxy-Setup)** - HTTPS with nginx/Caddy
- **[Scaling & Performance](Scaling-Performance)** - Optimization guide

---

**[← Back to Home](Home)** | **[Quick Start →](Quick-Start-Guide)**
