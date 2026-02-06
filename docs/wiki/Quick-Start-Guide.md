# Quick Start Guide

Get Nebulus Gantry running in **5 minutes** with Docker. This guide covers the fastest path to your first AI conversation.

For detailed setup options, see the [Installation Guide](Installation).

---

## Prerequisites

Before starting, ensure you have:

- ✅ **Docker & Docker Compose** (v2.0+) - [Install Docker](https://docs.docker.com/get-docker/)
- ✅ **OpenAI-compatible LLM API** - Running and accessible
  - TabbyAPI, Ollama, vLLM, LocalAI, or LM Studio
  - Note the host:port (e.g., `http://192.168.1.100:5000`)
- ✅ **ChromaDB** (optional) - For long-term memory features
  - Can skip for initial testing

**System requirements:**

- 4 GB RAM minimum (8 GB recommended)
- 10 GB disk space
- Linux, macOS, or Windows with WSL2

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/jlwestsr/nebulus-gantry.git
cd nebulus-gantry
```

---

## Step 2: Create Environment File

Create a `.env` file in the project root:

```bash
cat > .env << 'EOF'
# Database
DATABASE_URL=sqlite:///./data/gantry.db

# External Services (update TABBY_HOST with your LLM API endpoint)
CHROMA_HOST=http://chromadb:8000
TABBY_HOST=http://your-llm-host:5000

# Security (change SECRET_KEY in production!)
SECRET_KEY=dev-secret-change-in-production
SESSION_EXPIRE_HOURS=24

# Frontend
VITE_API_URL=http://localhost:8000
EOF
```

**⚠️ Important:** Replace `http://your-llm-host:5000` with your actual LLM API endpoint.

**Examples:**

```bash
# TabbyAPI on same machine
TABBY_HOST=http://192.168.1.100:5000

# Ollama on same machine
TABBY_HOST=http://192.168.1.100:11434

# LM Studio on same machine
TABBY_HOST=http://192.168.1.100:1234
```

**Network note:** If your LLM runs in Docker on the same host, use the Docker network name instead of localhost/IP.

---

## Step 3: Configure Docker Network

Gantry expects an external Docker network called `nebulus-prime_ai-network`:

```bash
# Check if network exists
docker network ls | grep nebulus

# If not found, create it
docker network create nebulus-prime_ai-network
```

**Alternative:** If you want to use a different network name, edit `docker-compose.yml`:

```yaml
networks:
  nebulus:
    external: true
    name: your-network-name  # Change this line
```

---

## Step 4: Launch Gantry

Start all services with Docker Compose:

```bash
# Start in background (production mode)
docker compose up -d

# Or start with logs visible (development mode)
docker compose up
```

**Wait 30-60 seconds** for services to initialize.

**Check status:**

```bash
docker compose ps

# Expected output:
# NAME                     STATUS              PORTS
# nebulus-gantry-backend   Up X seconds        0.0.0.0:8000->8000/tcp
# nebulus-gantry-frontend  Up X seconds        0.0.0.0:3001->3000/tcp
```

---

## Step 5: Create Admin User

Create your first user account with admin privileges:

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

**Important:** Use a strong password with:

- 12+ characters
- Mixed case letters
- Numbers
- Special characters

---

## Step 6: Access the Interface

Open your browser and navigate to:

🌐 **Frontend**: <http://localhost:3001>

You should see the Gantry login page.

**Other endpoints:**

- 🔧 **Backend API**: <http://localhost:8000>
- 📖 **API Docs (Swagger)**: <http://localhost:8000/docs>

---

## Step 7: Log In and Chat

1. **Log in** with the admin credentials you created
2. You'll be redirected to the chat interface
3. **Start a conversation** - type a message and press Enter
4. Watch the AI respond in real-time with streaming

**Test message ideas:**

- "Hello! Can you introduce yourself?"
- "What are your capabilities?"
- "Tell me about the weather in Paris"

---

## Verification Checklist

✅ **Backend health check:**

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

✅ **Frontend loads:**

- Navigate to <http://localhost:3001>
- Login page appears

✅ **Chat works:**

- Send a message
- Receive streaming response

✅ **LLM connection:**

```bash
docker compose logs backend | grep -i "llm"
# Should show successful LLM connection
```

✅ **ChromaDB connection** (if enabled):

```bash
docker compose logs backend | grep -i "chroma"
# Should show: "MemoryService: ChromaDB connected"
```

---

## Next Steps

Now that Gantry is running, explore these features:

### 📚 Upload a Document (Knowledge Vault)

1. Click **Knowledge Vault** in the sidebar
2. Click **Upload**
3. Select a PDF, DOCX, TXT, or CSV file
4. Wait for processing (status: "ready")
5. Chat with the AI - it can now reference the document!

### 👥 Create More Users

```bash
docker compose exec backend python -c "
from backend.services.auth_service import AuthService
from backend.database import get_engine, get_session_maker

engine = get_engine()
Session = get_session_maker(engine)
db = Session()
auth = AuthService(db)

user = auth.create_user(
    email='user@example.com',
    password='SecurePassword456!',
    role='user',
    display_name='Regular User'
)

print(f'✅ Created user: {user.email}')
db.close()
"
```

### 🔍 Search Conversations

- Press **Ctrl+K** (or Cmd+K on Mac)
- Type to search across all conversations
- Navigate with arrow keys, press Enter to jump

### 📌 Pin Important Conversations

- Click the pin icon on any conversation
- Pinned conversations stay at the top of the sidebar

### 📥 Export Conversations

1. Open a conversation
2. Click the **⋮** menu in the header
3. Choose **Export as JSON** or **Export as PDF**

### ⚙️ Admin Dashboard

As an admin user:

1. Click your profile icon (top right)
2. Select **Admin Dashboard**
3. Explore:
   - **Users tab** - Manage user accounts
   - **Models tab** - Switch between LLMs (TabbyAPI only)
   - **Services tab** - Monitor Docker containers
   - **Logs tab** - Stream real-time logs

---

## Stopping Gantry

```bash
# Stop services (keeps data)
docker compose down

# Stop and remove volumes (deletes data!)
docker compose down -v
```

---

## Troubleshooting

### Frontend won't load

**Error:** "Failed to fetch" or blank page

**Fix:**

```bash
# Check backend is running
curl http://localhost:8000/health

# Check frontend logs
docker compose logs frontend

# Restart frontend
docker compose restart frontend
```

### LLM connection fails

**Error:** "Failed to connect to LLM" in chat

**Fix:**

1. Verify your LLM API is running:

   ```bash
   curl http://your-llm-host:5000/v1/models
   ```

2. Check `TABBY_HOST` in `.env` matches your LLM endpoint
3. Verify Docker network connectivity:

   ```bash
   docker network inspect nebulus-prime_ai-network
   ```

4. Check backend logs:

   ```bash
   docker compose logs backend | grep -i llm
   ```

### Port conflicts

**Error:** "Address already in use"

**Fix:** Change ports in `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Change 8001 to any free port

  frontend:
    ports:
      - "3002:3000"  # Change 3002 to any free port
```

Then update `VITE_API_URL` in `.env`:

```bash
VITE_API_URL=http://localhost:8001
```

Rebuild:

```bash
docker compose down
docker compose up -d --build
```

### Database permission errors

**Error:** "Permission denied: './data/gantry.db'"

**Fix:**

```bash
mkdir -p data
chmod 777 data  # Development only - use proper permissions in production
docker compose restart backend
```

### ChromaDB not connecting

**Error:** "ChromaDB unavailable"

**Fix:**

1. Check if ChromaDB is running:

   ```bash
   curl http://localhost:8001/api/v1/heartbeat
   ```

2. If not running, start ChromaDB:

   ```bash
   docker run -d \
     --name chromadb \
     --network nebulus-prime_ai-network \
     -p 8001:8000 \
     -v chromadb-data:/chroma/chroma \
     chromadb/chroma:latest
   ```

3. ChromaDB is **optional** - Gantry works without it (no long-term memory features)

---

## Getting Help

Still stuck? Try these resources:

- 📖 **[Installation Guide](Installation)** - Detailed setup instructions
- 🔧 **[Configuration Guide](Configuration)** - Environment variables and settings
- 🐛 **[Common Issues](Common-Issues)** - FAQ and solutions
- 💬 **[GitHub Discussions](https://github.com/jlwestsr/nebulus-gantry/discussions)** - Ask the community
- 🐞 **[Report a Bug](https://github.com/jlwestsr/nebulus-gantry/issues)** - File an issue

---

## What's Next?

- **[Configuration](Configuration)** - Customize environment variables and settings
- **[Knowledge Vault](Knowledge-Vault)** - Deep dive into document upload and RAG
- **[Long-Term Memory](Long-Term-Memory)** - Vector search and knowledge graphs
- **[Admin Dashboard](Admin-Dashboard)** - User management and system monitoring
- **[Production Checklist](Production-Checklist)** - Secure your deployment for production use

---

**[← Back to Home](Home)** | **[Next: Configuration →](Configuration)**
