# Nebulus Gantry

The frontend and chat interface for the Nebulus AI ecosystem.

## API Documentation

Gantry exposes REST endpoints for external agent interaction:

### LTM (Long Term Memory)

Base path: `/api/conversations`

- `POST /`: Create a new conversation thread.
- `GET /{id}`: Retrieve full conversation history.
- `PUT /{id}`: Update conversation metadata (topic).
- `DELETE /{id}`: Delete a conversation.

## Standalone Development

Gantry can be run independently, but requires access to a Nebulus (Ollama/Chroma) backend.

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local dev)
- A running instance of Nebulus (or compatible Ollama endpoint)

### Running Locally (Docker)

```bash
# Start Gantry
./bin/gantry start

# Access at http://localhost:8080
```

### Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | URL of the Ollama API |
| `CHROMA_HOST` | `http://host.docker.internal:8000` | URL of the ChromaDB API |
| `CHAINLIT_AUTH_SECRET` | `dev-secret` | Secret for session signing |
| `DB_PATH` | `sqlite:///./data/gantry.db` | Database connection string |
