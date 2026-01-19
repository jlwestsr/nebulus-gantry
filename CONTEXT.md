# Project Context: Nebulus Gantry

## Overview
Nebulus Gantry is a local AI workspace and interface that serves as a bridge (or "gantry") between the user and the underlying Nebulus AI ecosystem. It provides a chat interface, notes management, and model/tool configuration capabilities.

## 🚨 Critical Operational Rules 🚨
Before performing any work on this project, you **MUST** review and adhere to the standards defined in:
👉 **[agent/rules/ai_behavior.md](agent/rules/ai_behavior.md)**

Key mandates include:
- **Mandatory `./venv/`**: System-level Python usage is strictly FORBIDDEN.
- **Frontend Architecture**: Pure JS-driven UI interacting with a Python REST API. No inline styles.
- **Linting**: Strict adherence to `flake8` (Python) and `eslint`/`stylelint` (Frontend).
- **Git Hooks**: Pre-commit validation is required.

## Architecture
- **Backend**: Python (FastAPI/Starlette) serving REST APIs.
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, and CSS3.
- **Database**: SQLite (via SQLAlchemy).
- **State Management**: Client-side state managed via encapsulated JS objects (e.g., `Nebulus.Notes`).

## Development Setup
1. **Python**: Ensure you have Python 3.12+ installed.
2. **Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Running**:
   ```bash
   uvicorn main:app --reload
   ```
