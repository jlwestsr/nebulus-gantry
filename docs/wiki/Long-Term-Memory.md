# Long-Term Memory

Guide to Gantry's long-term memory system powered by ChromaDB vector search and NetworkX knowledge graphs.

---

## Overview

Gantry's **Long-Term Memory (LTM)** system enables the AI to remember context across conversations and sessions using:

- **📊 Vector Search** - ChromaDB semantic search across all conversation history
- **🕸️ Knowledge Graphs** - NetworkX entity extraction and relationship mapping
- **🔄 Context Injection** - Relevant history automatically added to each prompt
- **🧠 Cross-Session Memory** - AI remembers from past conversations

**Key benefits:**

- AI recalls previous discussions even months later
- Better personalization and continuity
- Builds knowledge over time
- No manual context management needed

---

## How It Works

### Architecture

```text
User Message
     │
     ▼
┌─────────────────────────┐
│  Recent Conversation    │  ← Last 10 messages
│  History (SQLite)       │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Memory Search          │  ← Query: user message
│  (ChromaDB vectors)     │     Returns: relevant chunks
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Knowledge Graph        │  ← Extract: entities
│  (NetworkX JSON)        │     Returns: related concepts
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Context Assembly       │  ← Combines all sources
│  System Prompt +        │
│  Recent History +       │
│  Memory Chunks +        │
│  Graph Entities         │
└──────────┬──────────────┘
           │
           ▼
         LLM API
           │
           ▼
     AI Response
```

### Memory Storage

**Where memories live:**

- **User messages:** SQLite database (`messages` table)
- **Vector embeddings:** ChromaDB collections (`user_{user_id}_memory`)
- **Knowledge graph:** JSON files in SQLite (`conversation_graphs` table)

**What gets stored:**

- All user and assistant messages (full text)
- Vector embeddings of messages (semantic representation)
- Extracted entities and relationships (knowledge graph)

---

## Vector Memory (ChromaDB)

### How Vector Search Works

1. **Message stored:**
   - When you send a message, it's saved to SQLite
   - Text is converted to a **768-dimensional vector** (embedding)
   - Vector stored in ChromaDB with metadata (conversation_id, timestamp, role)

2. **Context retrieval:**
   - Your new message is embedded into a vector
   - ChromaDB finds **most similar vectors** (cosine similarity)
   - Top 5-10 relevant messages returned

3. **Injection:**
   - Relevant messages added to system prompt
   - LLM receives context: "User previously asked about X..."

**Example:**

```text
Today (new message):
"What was that Python library I asked about last week?"

ChromaDB finds (from 7 days ago):
"Can you explain how to use the pandas library for data analysis?"

Injected context:
"In a previous conversation, you asked about pandas for data analysis..."

LLM response:
"You were asking about pandas! It's great for data manipulation..."
```

### Collections

**Per-user isolation:**

- Each user has their own ChromaDB collection
- Collection name: `user_{user_id}_memory`
- Users cannot access each other's memories

**What's indexed:**

- User messages (your prompts and questions)
- Assistant responses (AI's answers)
- Timestamps and conversation IDs (for filtering)

### Embedding Model

**Default:** Sentence-BERT (`all-MiniLM-L6-v2`)

**Characteristics:**

- 384-dimensional vectors
- Fast inference (~50ms per message)
- Good general-purpose understanding
- Multilingual support

**Customization** (future):

- Swap embedding model in `backend/services/memory_service.py`
- Larger models (768-dim, 1024-dim) for better accuracy
- Domain-specific models (code, medical, legal)

---

## Knowledge Graphs (NetworkX)

### Entity Extraction

**Process:**

1. **LLM extracts entities** from conversation
2. Entities categorized: Person, Organization, Location, Concept, Tool, etc.
3. Relationships identified: "uses", "works_at", "located_in"
4. Graph updated with new nodes and edges

**Example conversation:**

```text
User: "I work at Acme Corp in San Francisco using Python and PostgreSQL"
Assistant: "Great! How long have you been using Python at Acme?"

Extracted graph:
Nodes:
  - Person("User")
  - Organization("Acme Corp")
  - Location("San Francisco")
  - Tool("Python")
  - Tool("PostgreSQL")

Edges:
  - User --[works_at]--> Acme Corp
  - Acme Corp --[located_in]--> San Francisco
  - User --[uses]--> Python
  - User --[uses]--> PostgreSQL
```

### Graph Storage

**Format:** JSON adjacency list stored in SQLite

```json
{
  "nodes": [
    {"id": "user_1", "type": "person", "label": "User"},
    {"id": "acme", "type": "organization", "label": "Acme Corp"},
    {"id": "python", "type": "tool", "label": "Python"}
  ],
  "edges": [
    {"source": "user_1", "target": "acme", "relation": "works_at"},
    {"source": "user_1", "target": "python", "relation": "uses"}
  ]
}
```

**Persistence:**

- Graph saved per conversation in `conversation_graphs` table
- Global user graph aggregates all conversations (future feature)
- Survives container rebuilds (stored in SQLite)

### Graph Queries

**When user asks:**

- "What technologies do I use?"
- "Where do I work?"
- "Tell me about my past projects"

**Graph search:**

- Query: Find all Tool nodes connected to User node
- Returns: Python, PostgreSQL, Docker, React, etc.
- LLM receives: "You've mentioned using: Python, PostgreSQL..."

**Benefits:**

- Structured knowledge (not just text search)
- Relationship awareness
- Long-term profile building

---

## Context Injection

### What Gets Injected

**System prompt structure:**

```text
[Base system prompt]

## Long-Term Memory Context

### Relevant Past Messages:
1. [7 days ago] User: "How do I configure PostgreSQL?"
   Assistant: "You can configure PostgreSQL using..."

2. [14 days ago] User: "I'm working on a Django project"
   Assistant: "For Django projects, I recommend..."

### User Profile:
- Works at: Acme Corp (San Francisco)
- Technologies: Python, PostgreSQL, Django, Docker
- Projects: E-commerce API, Analytics Dashboard

[Current conversation history]

[User's new message]
```

### Injection Strategy

**Selective injection:**

- Not all memories injected (context window limits)
- Top 5 most relevant vector matches
- Top 10 related graph entities
- Balance relevance vs. context size

**Relevance scoring:**

- Vector similarity (0.0 to 1.0)
- Recency boost (newer memories weighted higher)
- Conversation context (same topic preferred)

**Example:**

- User asks about "database optimization"
- ChromaDB finds: PostgreSQL config discussions
- Graph finds: PostgreSQL, Django, SQL tools
- Both injected for comprehensive context

---

## Memory Features

### Automatic Summarization

**Long conversations:**

- After 50+ messages, conversation auto-summarizes
- Summary stored as special message
- Reduces context size while preserving information

**Summary format:**

```text
CONVERSATION SUMMARY (Messages 1-50):
User is working on an e-commerce API using Django and PostgreSQL.
Key topics discussed:
- Database schema design for products and orders
- Payment gateway integration with Stripe
- Deployment using Docker Compose
- Performance optimization for product search
```

### Memory Decay (Future)

**Planned feature:**

- Older memories gradually weighted lower
- Importance scoring (frequently referenced = important)
- Manual memory pinning (mark as "always remember")

**Current:** All memories equally weighted (except recency boost)

### Memory Privacy

**Per-user isolation:**

- Your memories are only accessible to you
- Admin users cannot view user memories (privacy-first)
- No cross-user memory leakage

**Data control:**

- Delete account → all memories deleted
- Export memories (JSON) for backup
- Import memories (future feature)

---

## Disabling Memory

### Without ChromaDB

If ChromaDB is unavailable, Gantry falls back to:

- **Recent conversation history only** (last 10 messages)
- **No vector search** (no cross-session memory)
- **No knowledge graphs** (entity extraction disabled)

**Configuration:**

```bash
# Leave CHROMA_HOST unset or pointing to non-existent host
CHROMA_HOST=http://chromadb:8000

# Backend logs: "ChromaDB unavailable - memory features disabled"
```

**Impact:**

- AI still works normally
- Only remembers current conversation
- No long-term context or personalization

### Per-Conversation Disable

**Planned feature:** Toggle memory on/off per conversation

**Use cases:**

- Sensitive topics (don't save to memory)
- One-off queries (no need for context)
- Testing (clean slate)

---

## Troubleshooting

### Memory Not Working

**Issue:** AI doesn't remember previous conversations.

**Checks:**

```bash
# 1. Verify ChromaDB is running
curl http://localhost:8001/api/v1/heartbeat

# 2. Check backend logs for memory errors
docker compose logs backend | grep -i memory

# 3. Verify collections exist
curl http://localhost:8001/api/v1/collections
```

**Expected:** `user_{user_id}_memory` collection exists

### Inaccurate Memory

**Issue:** AI recalls wrong information from memory.

**Causes:**

- Vector similarity false positives
- Outdated information
- Ambiguous queries

**Solutions:**

- Be more specific in prompts: "In our conversation about X..."
- Correct AI: "No, that was about Y, not Z"
- Manually delete conversation if severely wrong

### Memory Latency

**Issue:** Responses slower with memory enabled.

**Causes:**

- ChromaDB query overhead (~50-200ms)
- Large result sets
- Network latency (Docker network)

**Solutions:**

- Reduce top_k (fewer memory chunks): default 10 → 5
- Use faster embedding model
- Optimize ChromaDB (persistent storage vs. memory)

### ChromaDB Connection Errors

**Error:** `Failed to connect to ChromaDB`

**Fixes:**

```bash
# Check ChromaDB container
docker ps | grep chroma

# Restart ChromaDB
docker restart chromadb

# Check network connectivity
docker network inspect nebulus-prime_ai-network

# Verify CHROMA_HOST in .env
cat .env | grep CHROMA_HOST
```

---

## Advanced Configuration

### Tune Memory Parameters

**Edit `backend/services/memory_service.py`:**

```python
# Number of memory chunks to retrieve
TOP_K_MEMORIES = 10  # Default: 10, Range: 5-20

# Minimum similarity threshold
SIMILARITY_THRESHOLD = 0.3  # Default: 0.3, Range: 0.0-1.0

# Recency boost (days)
RECENCY_BOOST_DAYS = 7  # Recent memories weighted higher
```

**Restart backend:**

```bash
docker compose restart backend
```

### Custom Embedding Model

**Replace default model:**

```python
# backend/services/memory_service.py
from sentence_transformers import SentenceTransformer

# Change model
self.embedding_model = SentenceTransformer('all-mpnet-base-v2')  # Better but slower
# Or
self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')  # Multilingual
```

**Rebuild ChromaDB:**

- Changing models requires re-embedding all messages
- Export conversations → delete ChromaDB volume → re-import

### Batch Re-Embedding

**When to use:**

- After changing embedding model
- Migrating from old version
- Corrupted embeddings

**Process:**

```python
# backend/scripts/reembed_all.py
from backend.services.memory_service import MemoryService
from backend.database import get_engine, get_session_maker
from backend.models import Message

engine = get_engine()
Session = get_session_maker(engine)
db = Session()

memory_service = MemoryService(db, user_id=1)

# Get all messages for user
messages = db.query(Message).filter(Message.user_id == 1).all()

# Re-embed
for msg in messages:
    memory_service.store_message(
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        message_id=msg.id
    )
    print(f"Re-embedded message {msg.id}")

db.close()
```

---

## Performance Metrics

### Memory Overhead

**Latency impact:**

- ChromaDB query: ~50-100ms (local), ~100-200ms (Docker network)
- Graph query: ~10-20ms (JSON parse + NetworkX)
- Embedding generation: ~30-50ms (per message)
- **Total:** ~100-250ms added to response time

**Storage:**

- Vector embeddings: ~3KB per message (768-dim float32)
- Knowledge graph: ~500B per node/edge
- 1000 messages = ~3MB vectors + ~100KB graph

### Scaling

**Per-user limits:**

- ChromaDB: Scales to millions of vectors
- Recommended: <100K messages per user (for performance)
- Auto-pruning (future): Delete oldest messages after threshold

**Multi-user:**

- Each user has isolated collection
- No cross-user performance impact
- ChromaDB handles hundreds of collections efficiently

---

## Best Practices

### Maximize Memory Utility

**Be descriptive:**
❌ "Do the thing we discussed"
✅ "Continue working on the Django e-commerce API we started yesterday"

**Reference past topics:**
❌ "What about that library?"
✅ "What was that Python library for data visualization we discussed last week?"

**Confirm understanding:**

- If AI recalls wrong context, correct it immediately
- Builds better future memory

### Organize Conversations

**Topic-based conversations:**

- One conversation per project/topic
- Helps memory search find relevant context
- Example: "Project Alpha - Backend", "Project Beta - Frontend"

**Use descriptive titles:**

- First message sets conversation title
- Be specific: "PostgreSQL Performance Optimization" vs. "Database Stuff"

---

## Next Steps

- **[Knowledge Vault](Knowledge-Vault)** - Upload documents for RAG-enhanced memory
- **[Chat Interface](Chat-Interface)** - Using the conversation UI
- **[Configuration](Configuration)** - Tune memory parameters

---

**[← Back to Home](Home)** | **[Knowledge Vault →](Knowledge-Vault)**
