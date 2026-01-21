---
trigger: always_on
---

# AI Agent Behavior & Operational Rules

**Project:** Nebulus Gantry
**Context:** Local AI Workspace (FastAPI + Vanilla JS)

## 0. Agent Configuration & Rule Hierarchy

When opening this project, the IDE looks first for rules in the local workspace folder before falling back to global system-wide rules.

### Rule Locations
| Type | Default File Path | Use Case |
|------|-------------------|----------|
| **Workspace Rule** | `nebulus-gantry/agent/rules/` | Project-specific coding standards (Strict Venv, FastAPI patterns). |
| **Global Rule** | `~/.gemini/GEMINI.md` | Universal behavior guidelines across all projects. |

## 1. Operational Guardrails (CRITICAL)
- **The VENV Mandate**: You generally CANNOT run `pip install` or `python` commands using the system interpreter. You **MUST** assume the virtual environment is active (`source venv/bin/activate`) or explicitly call `./venv/bin/python`.
- **Pre-Commit Verification**: Before marking any task as complete, the agent MUST run `pytest` and ensure all tests pass.
- **Linting Compliance**:
    - **Python**: Must pass `flake8` (max-line-length 88/120 depending on config).
    - **JS/CSS**: Must pass `eslint` or project-specific style checks.
- **No Shadow Logic**: Do not implement business logic that isn't requested. If a requirement is ambiguous, use `notify_user`.

## 2. Research & Discovery
- **Codebase Awareness**: Before creating a new service or utility:
    - Search `backend/app/` to check for existing FastAPI dependencies or utilities.
    - Check `frontend/static/js/` to ensure you aren't duplicating existing JS modules (e.g., `Nebulus.Notes`).
- **Dependency Check**: Do not add libraries to `requirements.txt` if standard library tools (like `json`, `sqlite3`, `pathlib`) or existing deps (`httpx`, `starlette`) suffice.

## 3. Communication Standards
- **Task Transparency**: Explain the *why* behind architecture decisions (e.g., "I chose `networkx` over a graph DB here because...").
- **Plan Approval**: For any change affecting the API Schema (`backend/app/models/`) or Core JS Architecture, create an `implementation_plan.md` first.

## 4. Coding Style (Backend - Python)
- **Type Hinting**: **Mandatory (Python 3.12+)**. Use `dict`, `list`, `Optional` from `typing` or standard collections. Use Pydantic models for API payloads.
- **Docstring Standard**: Google Style. Include "Args", "Returns", and "Raises".
- **FastAPI Patterns**:
    - Use `APIRouter` for modularity.
    - Use Dependency Injection (`Depends()`) for database sessions and services.
    - Never hardcode paths; use `pathlib` relative to project root.

## 5. Coding Style (Frontend - Vanilla JS)
- **No Frameworks**: Do NOT introduce React, Vue, or build steps (Webpack/Vite) unless explicitly directed.
- **Namespacing**: Do not pollute `window`. Wrap logic in global objects (e.g., `Nebulus.Chat`, `Nebulus.Config`).
- **Async/Await**: Use `fetch` with `async/await` for API calls.
- **DOM Manipulation**: Use `document.querySelector` and `element.classList`. Avoid inline `style="..."`.

## 6. Testing & Quality Assurance
- **Mandatory Unit Tests**:
    - **Backend**: New API endpoints must have tests in `tests/routers/`. Services must have tests in `tests/services/`.
    - **Frontend**: If complex logic exists (e.g., Markdown parsing), add a simple JS test or verification step.
- **System Verification**: Run `./scripts/run_tests.sh` (or `pytest`) before finalizing work.

## 7. Development Workflow
- **Conventional Commits**: Use `feat:`, `fix:`, `docs:`, `chore:`.
- **Python Environment**: STRICTLY use `./venv/`. Do NOT use `--break-system-packages`.
- **Git Tracking**:
    - **Main/Master**: Production releases only.
    - **Develop**: Integration branch.
    - **Feat/Fix**: Work branches. Always merge `develop` into your feature branch before PR.

## 8. Feature Implementation Workflow
When implementing a feature (e.g., "Add Memory Consolidation"):
0.  **Feature Doc**: Create `docs/features/feature_name.md` using the template.
1.  **Branch**: `git checkout -b feat/memory-consolidation`.
2.  **Backend Implementation**: Implement Pydantic models -> Service Logic -> API Router.
3.  **Frontend Implementation**: Add UI components -> Connect to API.
4.  **Test**: Run `pytest` and manual UI verification.
5.  **Merge**: Squash and merge to `develop`.

## 9. Tool Usage
- **Terminal**: Use terminal to verify file paths (`ls -F`, `tree`) before assuming structure.
- **Browser**: Use the browser to check documentation for `FastAPI`, `SQLAlchemy`, or specific `ChromaDB` client versions.
