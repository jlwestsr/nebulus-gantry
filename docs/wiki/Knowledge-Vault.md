# Knowledge Vault

Comprehensive guide to Gantry's Knowledge Vault - a Retrieval-Augmented Generation (RAG) system for uploading documents and getting AI answers with source citations.

---

## Overview

The **Knowledge Vault** transforms Gantry into a document-powered AI assistant capable of:

- **Document Upload** - PDF, DOCX, TXT, CSV file support
- **Automatic Processing** - Text extraction, smart chunking, vector embedding
- **Semantic Search** - Find relevant content across all documents
- **Source Citations** - AI responses reference specific document chunks
- **Collections** - Organize documents by project, topic, or category
- **Persistence** - All uploads survive container rebuilds

**Key benefits:**

- Ask questions about your documents
- Get answers with exact page/chunk references
- No manual data entry - just upload and query
- Private and secure - documents never leave your infrastructure

---

## How It Works

### RAG Pipeline

```text
User Uploads Document (PDF/DOCX/TXT/CSV)
           │
           ▼
┌──────────────────────┐
│  Text Extraction     │  ← pypdf, python-docx
│  PDF  → Text         │
│  DOCX → Text         │
│  TXT  → Text         │
│  CSV  → Text         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Smart Chunking      │  ← 2000 chars, 100 char overlap
│  Preserves context   │     Breaks at sentences/paragraphs
│  Overlapping chunks  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Vector Embedding    │  ← Sentence-BERT (384-dim)
│  Text → Vector       │     Semantic representation
│  Stored in ChromaDB  │
└──────────┬───────────┘
           │
           ▼
    Document Ready!


User Asks Question
           │
           ▼
┌──────────────────────┐
│  Semantic Search     │  ← ChromaDB cosine similarity
│  Find top 5 chunks   │     Relevance threshold: 0.3
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Context Assembly    │  ← System prompt + chunks
│  Inject into LLM     │     Include document metadata
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  AI Response         │  ← LLM generates answer
│  With Citations      │     References chunk IDs
└──────────────────────┘
```

---

## Getting Started

### Access the Knowledge Vault

1. **Log in** to Gantry
2. Click **Knowledge Vault** in the sidebar (📚 icon)
3. You'll see your collections (empty if first time)

### Create Your First Collection

**Collections** organize documents by topic/project.

1. Click **New Collection**
2. Enter details:
   - **Name**: "Project Documentation"
   - **Description**: "Technical docs for Project Alpha"
3. Click **Create**

**Collection created!** Now you can upload documents to it.

### Upload a Document

1. **Select a collection** or use "Default"
2. Click **Upload Document**
3. **Choose file** - PDF, DOCX, TXT, or CSV (max 50MB)
4. **Wait for processing** - Progress bar shows:
   - Text extraction
   - Chunking
   - Embedding (may take 30-60 seconds for large files)
5. **Status: Ready** - Document is searchable!

**Supported formats:**

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Extracts text from all pages |
| Word | `.docx` | Paragraphs and tables |
| Text | `.txt` | Plain text |
| CSV | `.csv` | Converted to text table |

---

## Using Documents in Chat

### Ask Questions

Once documents are uploaded, just ask questions in chat:

**Example:**

```text
You: "What does the user manual say about installation?"

AI: "According to the user manual (chunk 3), installation requires:
1. Python 3.12 or higher
2. Docker and Docker Compose
3. At least 8GB of RAM

The document also mentions (chunk 7) that you should create a .env file
before running docker compose up.

Sources: UserManual.pdf (chunks 3, 7)"
```

### How Citations Work

**Automatic citation:**

- AI searches your documents for relevant chunks
- Top 3-5 most relevant chunks injected into context
- AI references chunk IDs in response
- You can verify sources in Knowledge Vault

**Citation format:**

```text
"According to [DocumentName] (chunk X)..."
"As mentioned in [DocumentName] (page Y)..."
"Sources: Doc1.pdf (chunk 3), Doc2.docx (chunk 12)"
```

### Control Search Scope

**By default:** Searches all collections

**Limit search:**

- Select specific collection before asking
- Use explicit references: "In the Project Alpha docs, what does..."
- Mention document name: "According to requirements.pdf, what are..."

---

## Document Management

### View Documents

**In Knowledge Vault:**

1. Click **Knowledge Vault** in sidebar
2. Select a collection
3. View document list with:
   - Name
   - Upload date
   - Chunk count
   - Status (ready/processing/error)

**Document actions:**

- 🔍 **Preview** - View chunks and metadata
- 📥 **Download** - Re-download original text (not original file)
- 🗑️ **Delete** - Remove from vault and ChromaDB

### Search Within Vault

**Search bar** at top of Knowledge Vault:

1. Enter search query
2. Filters documents by name or content
3. Shows matching chunks with relevance scores
4. Click chunk to see full context

**Search tips:**

- Use specific terms: "API authentication" not "API"
- Try synonyms: "login" and "authentication"
- Longer queries often more accurate

### Update Documents

**To update a document:**

1. Delete old version
2. Upload new version

**Note:** Document updates are not automatic. If your source file changes, you must re-upload.

### Delete Documents

**Warning:** Deletion is permanent!

1. Select document
2. Click **Delete**
3. Confirm in dialog
4. Document removed from:
   - SQLite database (metadata)
   - ChromaDB (vector embeddings)

**Recovery:** Not possible - keep backups of important files

---

## Collections

### Why Use Collections?

**Organization:**

- Group related documents together
- Easier to find documents
- Scope searches to relevant topics

**Examples:**

- "Project Alpha - Technical Docs"
- "Meeting Notes - 2024"
- "Research Papers - Machine Learning"
- "Product Requirements"

### Create Collection

1. Click **New Collection**
2. Fill in form:
   - **Name** (required): Short, descriptive
   - **Description** (optional): Detailed explanation
3. Click **Create**

**Collection created!** Appears in sidebar list.

### Manage Collections

**Actions:**

- ✏️ **Edit** - Change name/description
- 📁 **View** - See all documents
- 🗑️ **Delete** - Remove collection and all documents (warning shown)

**Delete collection:**

- Deletes all documents inside
- Removes vector embeddings from ChromaDB
- Cannot be undone

### Default Collection

**Every user has a "Default" collection:**

- Created automatically on first document upload
- Cannot be deleted
- Used when no collection specified

---

## Advanced Features

### Chunking Strategy

**Why chunk documents?**

- LLMs have limited context windows (~8K-32K tokens)
- Full documents often exceed this limit
- Chunks allow precise retrieval

**Gantry's chunking:**

- **Chunk size:** 2000 characters (~500 tokens)
- **Overlap:** 100 characters (preserves context across boundaries)
- **Smart breaks:** Prefers paragraph or sentence boundaries
- **Metadata:** Each chunk tagged with document ID, chunk index, page number (if PDF)

**Example:**

```text
Document (5000 chars):
├─ Chunk 1: chars 0-2000
├─ Chunk 2: chars 1900-3900 (100 char overlap)
└─ Chunk 3: chars 3800-5000 (100 char overlap)
```

**Benefits:**

- Overlap ensures no context lost at boundaries
- Smart breaks avoid splitting sentences
- Smaller chunks = more precise retrieval

### Embedding Model

**Default:** Sentence-BERT `all-MiniLM-L6-v2`

**Characteristics:**

- 384-dimensional vectors
- Fast inference (~30ms per chunk)
- Good general-purpose understanding
- Multilingual support (50+ languages)

**Performance:**

- 100 chunks embedded in ~3 seconds
- 1000 chunks embedded in ~30 seconds

### Search Relevance

**How search works:**

1. **Query embedding:** Your question converted to vector
2. **Similarity search:** ChromaDB compares with all document chunks
3. **Ranking:** Cosine similarity score (0.0 to 1.0)
4. **Threshold:** Only chunks above 0.3 returned
5. **Top K:** Return 5 most relevant chunks

**Relevance scores:**

- **0.8-1.0:** Highly relevant (exact match)
- **0.5-0.8:** Relevant (same topic)
- **0.3-0.5:** Somewhat relevant (related concepts)
- **<0.3:** Not relevant (filtered out)

**Tuning search:**

Edit `backend/services/document_service.py`:

```python
# Number of chunks to retrieve
TOP_K_CHUNKS = 5  # Default: 5, Range: 3-10

# Minimum similarity threshold
SIMILARITY_THRESHOLD = 0.3  # Default: 0.3, Range: 0.2-0.5
```

### Metadata Extraction

**Automatically extracted:**

- **Filename:** Original upload name
- **File type:** PDF, DOCX, TXT, CSV
- **Upload date:** Timestamp
- **User ID:** Uploader
- **Collection ID:** Which collection
- **Total chunks:** Number of chunks created
- **File size:** Original file size

**PDF-specific:**

- **Page count:** Number of pages
- **Page mapping:** Which chunks came from which pages

**Future features:**

- Title extraction from document
- Author metadata
- Keywords/tags
- Custom metadata fields

---

## ChromaDB Integration

### Collections in ChromaDB

**Collection naming:**

- Format: `docs_{user_id}_{collection_id}`
- Example: `docs_1_5` (user 1, collection 5)
- Per-user, per-collection isolation

**What's stored:**

- **Documents:** Text chunks
- **Embeddings:** 384-dim vectors
- **Metadata:** document_id, chunk_index, collection_id, user_id
- **IDs:** Unique chunk identifiers

### Persistence

**ChromaDB data survives:**

- Container restarts
- Backend updates
- Frontend rebuilds

**Storage location:**

Docker volume: `nebulus-prime_chroma_data`

**Backup ChromaDB:**

```bash
# Backup volume
docker run --rm \
  -v nebulus-prime_chroma_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/chromadb-backup.tar.gz /data

# Restore volume
docker run --rm \
  -v nebulus-prime_chroma_data:/data \
  -v $(pwd):/backup \
  ubuntu tar xzf /backup/chromadb-backup.tar.gz -C /
```

### Verify ChromaDB

**Check connection:**

```bash
curl http://localhost:8001/api/v1/heartbeat
# Expected: {"nanosecond heartbeat": ...}
```

**List collections:**

```bash
curl http://localhost:8001/api/v1/collections
# Shows all document collections
```

---

## Performance Optimization

### Upload Performance

**Factors affecting speed:**

- **File size:** Larger files take longer to extract text
- **Chunk count:** More chunks = more embeddings = slower
- **Embedding model:** Faster models trade accuracy for speed

**Typical times:**

| File Size | Pages | Chunks | Upload Time |
|-----------|-------|--------|-------------|
| 100 KB | 10 | 10 | 5 seconds |
| 1 MB | 100 | 100 | 30 seconds |
| 10 MB | 1000 | 1000 | 5 minutes |
| 50 MB | 5000 | 5000 | 20 minutes |

**Optimization tips:**

- Upload smaller files when possible
- Split large PDFs into chapters
- Use text formats (TXT) instead of PDF for speed

### Search Performance

**Query latency:**

- **Embedding generation:** ~30ms
- **ChromaDB search:** ~50-100ms
- **Total:** ~100-200ms added to response time

**Scaling:**

- ChromaDB handles millions of chunks
- Performance degrades after ~100K chunks per collection
- Consider splitting large document sets into multiple collections

### Storage Estimates

**Per document:**

- **Metadata:** ~1KB (SQLite)
- **Vector embeddings:** ~1.5KB per chunk (ChromaDB)
- **Example:** 100-page PDF (~200 chunks) = 300KB vectors

**Scaling:**

- 1000 documents (~200K chunks) = ~300MB
- 10K documents (~2M chunks) = ~3GB

---

## Troubleshooting

### Upload Fails

**Error:** "Failed to extract text from PDF"

**Causes:**

- Scanned PDF (image-based, no text layer)
- Encrypted/password-protected PDF
- Corrupted file

**Solutions:**

- Use OCR tool to convert scanned PDF to text
- Remove password protection
- Try re-downloading file

**Error:** "File too large"

**Fix:** File exceeds 50MB limit

- Split PDF into smaller parts
- Compress file
- Extract text manually and upload as TXT

### Document Not Searchable

**Issue:** Uploaded document but AI doesn't reference it.

**Checks:**

```bash
# 1. Verify document status
# In Knowledge Vault: Status should be "ready"

# 2. Check ChromaDB collection exists
curl http://localhost:8001/api/v1/collections

# 3. Check backend logs for errors
docker compose logs backend | grep -i document
```

**Common causes:**

- Status stuck on "processing" - backend error during upload
- ChromaDB connection failed during embedding
- Document in different collection than expected

**Fix:** Re-upload document

### Inaccurate Results

**Issue:** AI cites wrong chunks or irrelevant content.

**Causes:**

- Query too vague
- Similarity threshold too low
- Document content ambiguous

**Solutions:**

- Be more specific in questions
- Mention document name: "In requirements.pdf, what..."
- Increase similarity threshold (edit document_service.py)
- Review chunk content in Knowledge Vault - may need better source material

### ChromaDB Connection Errors

**Error:** "ChromaDB unavailable"

**Fixes:**

```bash
# Check ChromaDB is running
docker ps | grep chroma

# Restart ChromaDB
docker restart chromadb

# Verify network connectivity
docker network inspect nebulus-prime_ai-network

# Check CHROMA_HOST in .env
cat .env | grep CHROMA_HOST
```

---

## Best Practices

### Document Preparation

**Before uploading:**

- ✅ **Clean formatting:** Remove headers/footers, page numbers
- ✅ **Logical structure:** Use headings and sections
- ✅ **Plain text:** Avoid heavy formatting, images, embedded objects
- ✅ **Descriptive filenames:** "ProjectAlpha_Requirements_v2.pdf" not "doc1.pdf"

**Avoid:**

- ❌ Scanned PDFs without OCR
- ❌ Password-protected files
- ❌ Massive single files (split instead)
- ❌ Image-heavy PDFs (text extraction fails)

### Organizing Documents

**Use collections effectively:**

- One collection per project/topic
- Group related documents together
- Keep collection names short and clear
- Add detailed descriptions

**Example structure:**

```text
Collections:
├─ Project Alpha - Requirements (10 docs)
├─ Project Alpha - Architecture (5 docs)
├─ Project Beta - User Research (20 docs)
└─ Company Policies (15 docs)
```

### Asking Questions

**Be specific:**

- ❌ "What does it say about APIs?"
- ✅ "What authentication methods does the API specification document describe?"

**Reference documents:**

- ❌ "How do I install it?"
- ✅ "How do I install the software according to the installation guide?"

**Follow up:**

- ❌ (Start new topic without context)
- ✅ "Can you elaborate on step 3 from the previous answer?"

### Maintaining the Vault

**Regular maintenance:**

- Delete outdated documents
- Re-upload updated versions
- Archive old collections
- Back up ChromaDB periodically

**Before major updates:**

```bash
# Backup ChromaDB data
docker run --rm -v nebulus-prime_chroma_data:/data \
  -v $(pwd):/backup ubuntu \
  tar czf /backup/chromadb-$(date +%Y%m%d).tar.gz /data
```

---

## API Usage

### Upload Document (API)

**Endpoint:** `POST /api/documents/upload`

**Headers:**

```text
Cookie: session_id=<your-session-cookie>
Content-Type: multipart/form-data
```

**Form data:**

```text
file: <binary file data>
collection_id: <collection ID or "default">
```

**Example (curl):**

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Cookie: session_id=abc123" \
  -F "file=@document.pdf" \
  -F "collection_id=5"
```

**Response:**

```json
{
  "id": 42,
  "filename": "document.pdf",
  "collection_id": 5,
  "status": "ready",
  "chunk_count": 127,
  "upload_date": "2026-02-06T10:30:00Z"
}
```

### Search Documents (API)

**Endpoint:** `GET /api/documents/search`

**Query params:**

- `q` - Search query (required)
- `collection_id` - Limit to collection (optional)
- `limit` - Max results (default: 5)

**Example:**

```bash
curl "http://localhost:8000/api/documents/search?q=API+authentication&limit=10" \
  -H "Cookie: session_id=abc123"
```

**Response:**

```json
{
  "results": [
    {
      "chunk_id": "doc_42_chunk_15",
      "document_id": 42,
      "document_name": "api_spec.pdf",
      "chunk_text": "API authentication uses OAuth 2.0...",
      "relevance_score": 0.87,
      "chunk_index": 15
    }
  ]
}
```

---

## Configuration

### Document Limits

**Edit `backend/services/document_service.py`:**

```python
# Maximum file size (bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Chunk size (characters)
CHUNK_SIZE = 2000  # ~500 tokens

# Chunk overlap (characters)
CHUNK_OVERLAP = 100

# Search top K results
TOP_K_CHUNKS = 5

# Similarity threshold
SIMILARITY_THRESHOLD = 0.3
```

### Embedding Model

**Change model:**

```python
# backend/services/document_service.py
from sentence_transformers import SentenceTransformer

# Faster but less accurate
model = SentenceTransformer('all-MiniLM-L6-v2')

# More accurate but slower
model = SentenceTransformer('all-mpnet-base-v2')

# Multilingual
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
```

**Note:** Changing models requires re-embedding all documents.

---

## Next Steps

- **[Long-Term Memory](Long-Term-Memory)** - Vector search and knowledge graphs for conversations
- **[Chat Interface](Chat-Interface)** - Using the conversation UI
- **[Admin Dashboard](Admin-Dashboard)** - User and system management

---

**[← Back to Home](Home)** | **[Admin Dashboard →](Admin-Dashboard)**
