# Project Context: Nebulus Gantry

## Overview

Nebulus Gantry is a local AI workspace and interface that serves as a bridge between the user and the underlying Nebulus AI ecosystem. It provides a chat interface, notes management, and model/tool configuration capabilities.

**Key Differentiator:** Gantry implements a **Hybrid Long-Term Memory (LTM)** system, allowing it to retain semantic context (Vectors) and factual associations (Knowledge Graph) across sessions.

## 🚨 Critical Operational Rules 🚨

**STOP & READ**: Before performing any work, you **MUST** review the detailed standards in:
👉 **[.agent/rules/ai_behavior.md](.agent/rules/ai_behavior.md)**

**The 4 Pillars of Gantry Development:**

1. **The VENV Mandate**: System-level Python usage is strictly FORBIDDEN. You must verify `./venv/` is active before running `pip` or `python`.
2. **Frontend Purity**: **Vanilla JavaScript (ES6+)** only. No React/Vue/Build steps. State is managed via global objects (e.g., `Nebulus.Chat`).
3. **Strict Linting**: Code must pass `flake8` (Python) and `eslint` (JS) before it is considered "done".
4. **No "Shadow Logic"**: Do not implement unrequested business logic.

## Architecture

### Backend (The Brain)

* **Framework**: Python 3.12+ (FastAPI / Starlette).
* **API Standards**: **All REST API usage must be Python**.
* **Database (State)**: SQLite (via SQLAlchemy) for application settings and notes.
* **Memory Engine (LTM)**:
  * **Semantic**: ChromaDB (External Service) for fuzzy vector retrieval.
  * **Associative**: NetworkX (In-Memory Graph, persisted to `data/graph.json`) for entity relationships.
  * **Consolidation**: Background `async` workers that summarize raw logs into "Golden Records."
* **LLM Engine**: Ollama (Port 11435).
  * **Note**: We run on port 11435 instead of the default 11434 to avoid conflicts with other local Ollama instances.

### Frontend (The Face)

* **Stack**: HTML5 (Living Standard), CSS3, Vanilla JavaScript (ES6+).
* **Communication**: REST API (Fetch with `async/await`).
* **Design Standards**:
  * **JavaScript**: Use **AJAX** for interactions. Target elements using **ID tags**.
  * **CSS**: Style elements using **class attributes** (avoid inline styles).
  * **Theme**: CSS Variables for theming.

## Directory Structure

The project follows a strict separation of concerns:

nebulus-gantry/
├── ansible/                   # Environment provisioning
├── bin/                       # Executable scripts (run_app, run_tests)
├── scripts/                   # Setup scripts (bootstrap.sh)
├── src/
│   └── nebulus_gantry/        # Main Package
│       ├── main.py            # App Entrypoint
│       ├── chat.py            # Chainlit Entrypoint
│       ├── routers/           # API Endpoints
│       ├── services/          # Business Logic
│       ├── ui/                # UI Components
│       └── public/            # Static Assets (CSS/JS)
├── data/                      # Local persistence
└── tests/                     # Pytest suite

## Development Setup

### 1. Environment Initialization

```bash
# Ensure you are in the project root
cd ~/projects/west_ai_labs/nebulus-gantry

# Bootstrap the environment (Ansible + Venv)
./scripts/bootstrap.sh
```

### 2. Running the App

```bash
# Start the server
./bin/run_app
```

### 3. Verification

Before committing code, run the full test suite:

```bash
./bin/run_tests
```

### 4. CLI Toolset

Use the `bin/gantry` wrapper for common operations:

* **Status**: `bin/gantry status` (Check services)
* **Start**: `bin/gantry start` (Run application)
* **Test**: `bin/gantry test` (Run unit tests)
* **Help**: `bin/gantry help` (Show commands)
