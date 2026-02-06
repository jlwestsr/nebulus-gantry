# Installation Guide

This guide covers installing Nebulus Gantry using Docker (recommended) or manually for development. Choose the method that fits your needs.

---

## 📋 Prerequisites

Before installing Gantry, ensure you have:

### Required

- **Docker & Docker Compose** (v2.0+) - [Install Docker](https://docs.docker.com/get-docker/)
- **OpenAI-compatible LLM API** - One of:
  - [TabbyAPI](https://github.com/theroyallab/tabbyAPI) (recommended)
  - [Ollama](https://ollama.ai/)
  - [vLLM](https://github.com/vllm-project/vllm)
  - [LocalAI](https://localai.io/)
  - [LM Studio](https://lmstudio.ai/)

### Optional but Recommended

- **ChromaDB** - For long-term memory features
  - Can run via Docker or use existing instance
  - [ChromaDB Installation](https://docs.trychroma.com/deployment)

### System Requirements

**Minimum:**

- 2 CPU cores
- 4 GB RAM
- 10 GB disk space

**Recommended:**

- 4+ CPU cores
- 8+ GB RAM
- 20+ GB disk space (for logs, database, documents)

---

## 🐳 Docker Installation (Recommended)

Docker is the fastest way to get Gantry running in production or development.

### 1. Clone the Repository

```bash
git clone https://github.com/jlwestsr/nebulus-gantry.git
cd nebulus-gantry
```

### 2. Create Environment File

Create a `.env` file with your configuration:

```bash
cat > .env << 'EOF'
# Database
DATABASE_URL=sqlite:///./data/gantry.db

# External Services
CHROMA_HOST=http://chromadb:8000
TABBY_HOST=http://your-llm-host:5000

# Security
SECRET_KEY=change-this-to-a-random-32-character-string
SESSION_EXPIRE_HOURS=24

# Frontend (build-time variable)
VITE_API_URL=http://localhost:8000
EOF
```

**Important configuration notes:**

| Variable | Description | Example |
|----------|-------------|---------|
| `TABBY_HOST` | Your LLM API endpoint | `http://192.168.1.100:5000` |
| `CHROMA_HOST` | ChromaDB endpoint (optional) | `http://chromadb:8000` |
| `SECRET_KEY` | Random string for session signing | Generate with `openssl rand -hex 32` |

### 3. Configure Docker Network

Gantry expects an external Docker network to connect to your LLM services:

```bash
# Check if network exists
docker network ls | grep nebulus

# If not, create it
docker network create nebulus-prime_ai-network
```

**Or** modify `docker-compose.yml` to use a different network:

```yaml
networks:
  nebulus:
    external: true
    name: your-network-name  # Change this
```

### 4. Launch Gantry

```bash
# Production mode (daemon)
docker compose up -d

# Development mode (with logs)
docker compose up

# Or use the convenience script
bin/gantry start
```

**What happens:**

- Backend builds (FastAPI + Python dependencies)
- Frontend builds (React + npm dependencies)
- Containers start on ports 8000 (backend) and 3001 (frontend)
- SQLite database initializes in `./data/gantry.db`

### 5. Verify Services

```bash
# Check container status
docker compose ps

# Expected output:
# NAME                     STATUS              PORTS
# nebulus-gantry-backend   Up X minutes        0.0.0.0:8000->8000/tcp
# nebulus-gantry-frontend  Up X minutes        0.0.0.0:3001->3000/tcp

# Check logs
docker compose logs backend
docker compose logs frontend
```

### 6. Create Admin User

```bash
docker compose exec backend python -c "
from backend.services.auth_service import AuthService
from backend.database import get_engine, get_session_maker

engine = get_engine()
Session = get_session_maker(engine)
db = Session()
auth = AuthService(db)

user = auth.create_user(
    email='admin@example.com',
    password='YourSecurePassword123!',
    role='admin',
    display_name='Admin'
)

print(f'✅ Created admin user: {user.email}')
db.close()
"
```

**Security note:** Use a strong password with 12+ characters, mixed case, numbers, and symbols.

### 7. Access the Application

Open your browser:

- **Frontend UI**: <http://localhost:3001>
- **Backend API**: <http://localhost:8000>
- **API Docs (Swagger)**: <http://localhost:8000/docs>

Log in with the admin credentials you created.

---

## 🔧 Manual Installation (Development)

For local development without Docker, you'll need Python 3.12+ and Node.js 20+.

### Backend Setup

#### 1. Install Python Dependencies

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment

```bash
# Create .env in backend directory
cat > .env << 'EOF'
DATABASE_URL=sqlite:///./data/gantry.db
CHROMA_HOST=http://localhost:8001
TABBY_HOST=http://localhost:5000
SECRET_KEY=dev-secret-change-in-production
SESSION_EXPIRE_HOURS=24
EOF
```

#### 3. Initialize Database

```bash
# The database auto-creates on first run
# Or manually trigger creation:
python -c "
from backend.database import get_engine, Base
from backend.models import *  # Import all models
engine = get_engine()
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
```

#### 4. Create Admin User

```bash
python -c "
from backend.services.auth_service import AuthService
from backend.database import get_engine, get_session_maker

engine = get_engine()
Session = get_session_maker(engine)
db = Session()
auth = AuthService(db)

user = auth.create_user(
    email='admin@localhost',
    password='admin123',
    role='admin',
    display_name='Admin'
)

print(f'Created: {user.email}')
db.close()
"
```

#### 5. Start Backend Server

```bash
# Development server with hot reload
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Production server (no reload)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Backend will be available at <http://localhost:8000>

### Frontend Setup

#### 1. Install Node Dependencies

```bash
cd frontend
npm install
```

#### 2. Configure Environment

```bash
# Create .env in frontend directory
cat > .env << 'EOF'
VITE_API_URL=http://localhost:8000
EOF
```

#### 3. Start Development Server

```bash
# Development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

Frontend dev server will be at <http://localhost:5173>

---

## 🔌 LLM Backend Setup

Gantry requires an OpenAI-compatible API endpoint. Choose one:

### Option 1: TabbyAPI (Recommended)

Best integration with model switching support.

```bash
# Install TabbyAPI
git clone https://github.com/theroyallab/tabbyAPI.git
cd tabbyAPI
pip install -r requirements.txt

# Download a model (example: Qwen2.5-Coder-7B)
# Place in models/ directory

# Start TabbyAPI
python main.py --host 0.0.0.0 --port 5000
```

Configure in Gantry:

```bash
TABBY_HOST=http://localhost:5000
```

### Option 2: Ollama

Easy installation, great for macOS.

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download a model
ollama pull llama3.1:8b

# Ollama runs on port 11434 by default
```

Configure in Gantry:

```bash
TABBY_HOST=http://localhost:11434
```

### Option 3: vLLM

High-performance production server.

```bash
# Install vLLM
pip install vllm

# Start server with a model
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --host 0.0.0.0 \
  --port 5000
```

Configure in Gantry:

```bash
TABBY_HOST=http://localhost:5000
```

### Option 4: LM Studio

Desktop application with GUI.

1. Download from <https://lmstudio.ai/>
2. Load a model
3. Go to **Developer** tab
4. Click **Start Server** (default port: 1234)

Configure in Gantry:

```bash
TABBY_HOST=http://localhost:1234
```

---

## 🧠 ChromaDB Setup (Optional)

ChromaDB enables long-term memory features. You can run it via Docker or install locally.

### Docker (Recommended)

```bash
docker run -d \
  --name chromadb \
  --network nebulus-prime_ai-network \
  -p 8001:8000 \
  -v chromadb-data:/chroma/chroma \
  chromadb/chroma:latest
```

Configure in Gantry:

```bash
CHROMA_HOST=http://chromadb:8000  # If on same Docker network
# OR
CHROMA_HOST=http://localhost:8001  # If accessing from host
```

### Local Installation

```bash
pip install chromadb

# Start ChromaDB server
chroma run --host 0.0.0.0 --port 8001
```

Configure in Gantry:

```bash
CHROMA_HOST=http://localhost:8001
```

### Verify ChromaDB

```bash
curl http://localhost:8001/api/v1/heartbeat
# Should return: {"nanosecond heartbeat": ...}
```

---

## ✅ Post-Installation Verification

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### 2. Check Frontend

Open <http://localhost:3001> - you should see the login page.

### 3. Test Login

Log in with your admin credentials. You should be redirected to the chat interface.

### 4. Test LLM Connection

Send a test message in the chat. If you see a streaming response, the LLM connection is working.

### 5. Test Memory (if ChromaDB enabled)

Check backend logs for ChromaDB connection:

```bash
docker compose logs backend | grep -i chroma
# Should see: "MemoryService: ChromaDB connected"
```

### 6. Test Document Upload

1. Click **Knowledge Vault** in sidebar
2. Click **Upload**
3. Upload a text file
4. Check that status shows "ready"

---

## 🐛 Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

- **Fix:** Ensure virtual environment is activated and dependencies installed

  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

**Error:** `Database is locked`

- **Fix:** SQLite is being accessed by multiple processes

  ```bash
  # Stop all Gantry processes
  docker compose down
  # Restart
  docker compose up -d
  ```

### Frontend won't connect to backend

**Error:** `Failed to fetch` or CORS errors

- **Fix:** Check `VITE_API_URL` in frontend `.env`
- **Fix:** Ensure backend is running on port 8000
- **Fix:** Check CORS settings in `backend/main.py`

### LLM connection fails

**Error:** `Failed to connect to LLM`

- **Fix:** Verify LLM service is running: `curl http://your-llm-host:5000/v1/models`
- **Fix:** Check `TABBY_HOST` in `.env`
- **Fix:** Ensure Docker network connectivity if using containers

### ChromaDB not connecting

**Error:** `ChromaDB unavailable`

- **Fix:** Verify ChromaDB is running: `curl http://localhost:8001/api/v1/heartbeat`
- **Fix:** Check `CHROMA_HOST` in `.env`
- **Fix:** ChromaDB is optional - Gantry will work without it (no memory features)

### Port conflicts

**Error:** `Address already in use`

- **Fix:** Change ports in `docker-compose.yml`:

  ```yaml
  ports:
    - "8001:8000"  # Backend (change 8001)
    - "3002:3000"  # Frontend (change 3002)
  ```

### Permission denied on data directory

**Error:** `Permission denied: './data/gantry.db'`

- **Fix:** Create data directory with correct permissions

  ```bash
  mkdir -p data
  chmod 777 data  # Development only
  ```

---

## 🔄 Updating Gantry

### Docker Update

```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker compose up -d --build

# Or use convenience script
bin/gantry rebuild
```

### Manual Update

```bash
# Pull latest code
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Update frontend
cd ../frontend
npm install

# Restart services
```

---

## 🚀 Next Steps

Now that Gantry is installed:

1. **[Configuration Guide](Configuration)** - Customize settings
2. **[Knowledge Vault](Knowledge-Vault)** - Upload your first document
3. **[Admin Dashboard](Admin-Dashboard)** - Explore admin features
4. **[Production Checklist](Production-Checklist)** - Secure your deployment

---

## 💬 Getting Help

- **Issues?** Check [Common Issues](Common-Issues)
- **Questions?** Open a [GitHub Discussion](https://github.com/jlwestsr/nebulus-gantry/discussions)
- **Bugs?** [Report an issue](https://github.com/jlwestsr/nebulus-gantry/issues)

---

**[← Back to Home](Home)** | **[Next: Configuration →](Configuration)**
