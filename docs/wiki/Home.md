# Nebulus Gantry Documentation

Welcome to the comprehensive documentation for **Nebulus Gantry** — a production-ready, self-hosted AI chat interface with memory, RAG, and enterprise features.

![Gantry Interface](https://raw.githubusercontent.com/jlwestsr/nebulus-gantry/main/docs/images/gantry-interface.png)

---

## 🎯 What is Nebulus Gantry?

Nebulus Gantry is a complete web application for deploying your own AI assistant with:

- **Beautiful chat interface** - Dark-themed, Claude.AI-inspired UI
- **Long-term memory** - ChromaDB vectors + knowledge graphs
- **Knowledge Vault (RAG)** - Upload documents, get cited answers
- **Multi-user admin** - Role-based auth, model switching, logs
- **Flexible backend** - Works with TabbyAPI, Ollama, vLLM, and any OpenAI-compatible API

**Perfect for:**

- Developers wanting a self-hosted ChatGPT alternative
- Enterprises requiring private AI deployment
- AI enthusiasts running local LLMs (Llama, Mistral, Qwen, etc.)

---

## 📚 Documentation Sections

### Getting Started

- **[Installation](Installation)** - Docker and manual setup instructions
- **[Quick Start Guide](Quick-Start-Guide)** - Get running in 5 minutes
- **[Configuration](Configuration)** - Environment variables and settings

### Features

- **[Chat Interface](Chat-Interface)** - Using the conversation UI
- **[Long-Term Memory](Long-Term-Memory)** - Vector search and knowledge graphs
- **[Knowledge Vault](Knowledge-Vault)** - Document upload and RAG
- **[Admin Dashboard](Admin-Dashboard)** - Users, models, services, logs
- **[Model Switching](Model-Switching)** - Hot-swap LLMs without restart

### Deployment & Operations

- **[Docker Deployment](Docker-Deployment)** - Production setup with Docker Compose
- **[Production Checklist](Production-Checklist)** - Security, HTTPS, backups
- **[Reverse Proxy Setup](Reverse-Proxy-Setup)** - Nginx, Caddy, Traefik
- **[Scaling & Performance](Scaling-Performance)** - Optimization tips

### For Developers

- **[Architecture](Architecture)** - System design and data flow
- **[API Reference](API-Reference)** - REST endpoints and SSE streaming
- **[Development Setup](Development-Setup)** - Local dev environment
- **[Testing](Testing)** - Running and writing tests
- **[Contributing](Contributing)** - How to contribute

### Troubleshooting

- **[Common Issues](Common-Issues)** - FAQ and solutions
- **[Debugging Guide](Debugging-Guide)** - Logs, errors, diagnostics

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI-compatible LLM API (TabbyAPI, Ollama, vLLM)
- ChromaDB instance (optional but recommended)

### 1. Clone and Configure

```bash
git clone https://github.com/jlwestsr/nebulus-gantry.git
cd nebulus-gantry

# Create environment file
cat > .env << 'EOF'
DATABASE_URL=sqlite:///./data/gantry.db
CHROMA_HOST=http://chromadb:8000
TABBY_HOST=http://your-llm-api:5000
SECRET_KEY=change-this-to-a-random-secret
SESSION_EXPIRE_HOURS=24
VITE_API_URL=http://localhost:8000
EOF
```

### 2. Launch with Docker

```bash
docker compose up -d
```

### 3. Create Admin User

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
    password='your-secure-password',
    role='admin',
    display_name='Admin'
)
print(f'Created: {user.email}')
db.close()
"
```

### 4. Access the Interface

- Frontend: <http://localhost:3001>
- Backend API: <http://localhost:8000>
- API Docs: <http://localhost:8000/docs>

**See [Installation Guide](Installation) for detailed setup instructions.**

---

## 🏗️ Architecture Overview

```text
┌─────────────────────────────────────────────────────────┐
│                  Browser (React SPA)                     │
│  ┌────────┬────────┬────────┬──────────┬──────────┐    │
│  │ Chat   │ Vault  │ Admin  │ Settings │ Search   │    │
│  └────────┴────────┴────────┴──────────┴──────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────▼──────────────────────────────────┐
│               FastAPI Backend                            │
│  ┌────────────────────────────────────────────────┐     │
│  │ Routes: /auth /chat /admin /documents          │     │
│  ├────────────────────────────────────────────────┤     │
│  │ Services: Auth│Chat│LLM│Memory│Graph│Docs      │     │
│  └────────────────────────────────────────────────┘     │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │ SQLite   │ ChromaDB │ NetworkX │ LLM API  │         │
│  │ (users,  │ (vectors)│ (graph)  │ (stream) │         │
│  │ messages)│          │          │          │         │
│  └──────────┴──────────┴──────────┴──────────┘         │
└─────────────────────────────────────────────────────────┘
```

**Learn more:** [Architecture Documentation](Architecture)

---

## 💡 Key Features

### 🧠 Long-Term Memory

- **Vector search** across all conversation history
- **Knowledge graphs** extracting entities and relationships
- **Context injection** - Relevant history added to each prompt
- **Cross-session memory** - AI remembers across multiple conversations

[Read more →](Long-Term-Memory)

### 📚 Knowledge Vault (RAG)

- **Document upload** - PDF, DOCX, TXT, CSV support
- **Smart chunking** - 2000 chars with overlap for context
- **Semantic search** - Vector embeddings for accurate retrieval
- **Source citations** - Responses reference specific chunks
- **Collections** - Organize documents by topic
- **Persistence** - Survives container rebuilds

[Read more →](Knowledge-Vault)

### 👥 Multi-User & Admin

- **Role-based auth** - Admin and user roles
- **User management** - CRUD operations via dashboard
- **Model switching** - Hot-swap LLMs (TabbyAPI integration)
- **Service monitoring** - Docker container status
- **Log streaming** - Real-time logs via SSE
- **Audit trail** - Track user actions

[Read more →](Admin-Dashboard)

---

## 🔌 Backend Compatibility

Gantry works with any **OpenAI-compatible API**:

| Backend | Support | Notes |
|---------|---------|-------|
| **TabbyAPI** | ✅ Full | Recommended, includes model switching |
| **Ollama** | ✅ Full | Works with all models (Llama, Mistral, etc.) |
| **vLLM** | ✅ Full | Production inference server |
| **LocalAI** | ✅ Full | All-in-one local inference |
| **LM Studio** | ✅ Full | Desktop LLM server |
| **text-generation-webui** | ✅ Full | OpenAI API extension |
| **OpenAI API** | ✅ Full | Cloud option (not private) |

**Memory (ChromaDB)** - Optional but recommended for long-term memory features

[Configuration Guide →](Configuration)

---

## 🎯 Use Cases

### For Developers

- Complete control over AI infrastructure
- Clean FastAPI + React architecture
- Full API access for integrations
- Docker-first deployment
- Extensible and customizable

### For Enterprises

- Private deployment (GDPR, HIPAA, SOC2)
- Multi-user with role-based access
- Audit logs and conversation exports
- Security-first design
- No vendor lock-in

### For AI Enthusiasts

- Beautiful UI for local LLMs
- Built-in RAG for document queries
- Memory system remembers context
- One-command Docker deployment
- Claude.AI-inspired UX

---

## 📖 Learning Path

**New to Gantry?** Follow this path:

1. **[Installation](Installation)** - Get it running
2. **[Quick Start Guide](Quick-Start-Guide)** - First conversation
3. **[Knowledge Vault](Knowledge-Vault)** - Upload a document
4. **[Configuration](Configuration)** - Customize settings
5. **[Admin Dashboard](Admin-Dashboard)** - Explore admin features

**Deploying to production?**

1. **[Production Checklist](Production-Checklist)** - Security hardening
2. **[Docker Deployment](Docker-Deployment)** - Production setup
3. **[Reverse Proxy Setup](Reverse-Proxy-Setup)** - HTTPS configuration
4. **[Scaling & Performance](Scaling-Performance)** - Optimization

**Want to contribute?**

1. **[Architecture](Architecture)** - Understand the system
2. **[Development Setup](Development-Setup)** - Local environment
3. **[Testing](Testing)** - Run and write tests
4. **[Contributing](Contributing)** - Contribution guidelines

---

## 🆘 Getting Help

**Found a bug?** [Open an issue](https://github.com/jlwestsr/nebulus-gantry/issues)

**Have a question?** Check the [Common Issues](Common-Issues) page first

**Want to contribute?** See the [Contributing Guide](Contributing)

**Need commercial support?** Contact: <jason@westailabs.com>

---

## 🔗 External Links

- **[Main Repository](https://github.com/jlwestsr/nebulus-gantry)** - Source code
- **[Issue Tracker](https://github.com/jlwestsr/nebulus-gantry/issues)** - Bugs and features
- **[Discussions](https://github.com/jlwestsr/nebulus-gantry/discussions)** - Community Q&A

**Related Projects:**

- [Nebulus Prime](https://github.com/jlwestsr/nebulus-prime) - Linux AI infrastructure
- [Nebulus Edge](https://github.com/jlwestsr/nebulus-edge) - macOS deployment
- [Nebulus Core](https://github.com/jlwestsr/nebulus-core) - Shared library

---

## 📊 Project Status

- ✅ **v2.0** - Complete rewrite (FastAPI + React)
- ✅ **Streaming chat** - SSE real-time responses
- ✅ **Long-term memory** - ChromaDB + NetworkX
- ✅ **Knowledge Vault** - RAG with document upload
- ✅ **Admin panel** - Users, models, services, logs
- ✅ **Model switching** - Hot-swap LLMs
- ✅ **Conversation export** - JSON and PDF
- ✅ **Searchable history** - Ctrl+K command palette
- 🚧 **Personas** - Custom system prompts (planned)
- 🚧 **Multi-modal** - Image upload (planned)

---

**Ready to get started?** Head to the [Installation Guide](Installation) →

*Documentation last updated: 2026-02-06*
