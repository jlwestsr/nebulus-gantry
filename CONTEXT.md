# Project Context: Nebulus Gantry

## Overview

Nebulus Gantry is a local AI workspace and interface that serves as a bridge between the user and the underlying Nebulus AI ecosystem. It provides a chat interface, notes management, and model/tool configuration capabilities.

**Key Differentiator:** Gantry implements a **Hybrid Long-Term Memory (LTM)** system, allowing it to retain semantic context (Vectors) and factual associations (Knowledge Graph) across sessions.

## 🚨 Critical Operational Rules 🚨

**STOP & READ**: Before performing any work, you **MUST** review the detailed standards in:
👉 **[.agent/rules/ai_behavior.md](.agent/rules/ai_behavior.md)**

### Reference Material (READ-ONLY)

The following directories are symlinks to external projects provided for architectural reference only. **ABSOLUTELY NO CHANGES** are permitted in these directories:

* `reference_nebulus/`: The core Nebulus logic.
* `reference_open-webui/`: The Open WebUI project.

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

### Asset Versioning & Cache Busting

To ensure users receive updated CSS/JS assets, we use a query parameter versioning strategy (e.g., `style.css?v=44`).

**CRITICAL: When modifying `public/style.css` or `public/script.js`, you MUST update the version number in TWO places:**

1. **Codebase (Custom Pages)**: Increment `UI_CSS_VERSION` or `UI_JS_VERSION` in `src/nebulus_gantry/version.py`.
2. **Chainlit Config (Main App)**: Update `custom_css` or `custom_js` paths in `.chainlit/config.toml` (e.g., `custom_css = "/public/style.css?v=44"`).

**After updating `.chainlit/config.toml`, you MUST rebuild/restart the Docker container for changes to take effect.**

## Directory Structure

The project follows a strict separation of concerns:

nebulus-gantry/
├── reference_nebulus/         # [READ-ONLY] Nebulus Reference
├── reference_open-webui/      # [READ-ONLY] Open WebUI Reference
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

### 2. Running Application & Tests (The ONE Way)

All operations **MUST** be performed via the **Gantry CLI**. Custom scripts (`bin/run_app`, `bin/run_tests`) have been **deprecated/removed**.

```bash
# Start the full stack (Docker)
./bin/gantry start

# Stop the stack
./bin/gantry stop

# Run unit tests (Local)
./bin/gantry test

# Check container status
./bin/gantry status

# Rebuild containers (e.g. after requirements.txt change)
./bin/gantry rebuild

# Run full pre-commit validation
./bin/gantry validate

# View logs
./bin/gantry logs
```

**Rule**: NEW CLI/Script definitions MUST be implemented as subcommands in `bin/gantry`. Do not create standalone scripts in `bin/`.
