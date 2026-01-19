# Nebulus Gantry

The frontend and chat interface for the Nebulus AI ecosystem.

## Standalone Development

Gantry can be run independently, but requires access to a Nebulus (Ollama/Chroma) backend.

### Prerequisites
- Docker & Docker Compose
- A running instance of Nebulus (or compatible Ollama endpoint)

### Running Locally

```bash
# Start Gantry
docker-compose up --build
```

### Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | URL of the Ollama API |
| `CHROMA_HOST` | `http://host.docker.internal:8000` | URL of the ChromaDB API |
| `CHAINLIT_AUTH_SECRET` | `dev-secret` | Secret for session signing |
| `DB_PATH` | `sqlite:///./data/gantry.db` | Database connection string |
