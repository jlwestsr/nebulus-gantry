# AI Directives for Nebulus Gantry

These rules are critical for any AI agent working on this project. They encode the architectural standards, quality requirements, and behavioral expectations for developing Nebulus Gantry.

## 1. Discovery-Driven Development

- **Ground Truth**: Before proposing any changes, check existing architecture in `backend/` and `frontend/src/`.
- **Reference Awareness**: Use `CONTEXT.md` as the authoritative description of patterns and conventions.
- **No Assumptions**: Do not implement features based on "general knowledge." Implement them based on the existing codebase patterns.
- **Read Before Writing**: Always read the relevant source files before modifying them. Understand what exists before suggesting changes.

## 2. Architecture Standards

- **Docker-First**: The canonical deployment is Docker Compose. All services must work within the container network `nebulus_ai-network`.
- **Container Networking**: Services reference each other by container hostname (e.g., `chromadb`, `tabby`), not `localhost` or `host.docker.internal`.
- **Environment Variables**: All configuration flows through environment variables defined in `docker-compose.yml` and `backend/config.py`. Never hardcode endpoints or secrets.
- **API Design**: All backend routes live under `/api/` with three routers: `auth`, `chat`, `admin`.
- **Graceful Degradation**: ChromaDB, NetworkX, Docker, and TabbyAPI failures must be caught and logged. The app continues operating without those features.

## 3. Testing & Quality Assurance

- **Mandatory Unit Tests**: All backend changes must include or update tests in `backend/tests/`.
- **Pre-Commit Hooks**: The following hooks run automatically and must pass with zero errors:
  - `flake8` (Python linting, max-line-length 120)
  - `eslint` (JavaScript linting)
  - `stylelint` (CSS linting)
  - `pytest` (backend tests)
  - `markdownlint` (documentation)
  - `yamllint` (YAML files)
- **Pre-Completion Verification**: Run `bin/gantry validate` (or `pre-commit run --all-files`) before marking any task as complete.

## 4. Development Workflow

- **Conventional Commits**: Use `feat:`, `fix:`, `docs:`, or `chore:` prefixes on all commit messages.
- **No Direct Work on Main**: Never commit directly to `main`. Always use feature branches.
- **Branch Naming**: `feat/`, `fix/`, `docs/`, `chore/` prefixes. Feature branches are local only unless long-lived.
- **Push Authorization**: Never push to remote without explicit user approval.

## 5. Coding Style

### Python (Backend)

- Type hints mandatory on all function signatures
- `flake8` compliance (max-line-length 120)
- Google-style docstrings on public functions
- SQLAlchemy 2 style (select statements, not legacy query API)

### TypeScript (Frontend)

- Strict TypeScript mode
- Functional components only (no class components)
- Zustand stores for all shared state (no prop drilling)
- Tailwind CSS v4 utility classes for styling
- No inline styles except for dynamic values

## 6. Agentic Artifact Protocol

- **Task Tracking**: For complex tasks, maintain a task artifact to track progress.
- **Implementation Plans**: Before multi-file changes, create an implementation plan for user approval.
- **Feature Specs**: Document significant features in `docs/features/` using `docs/feature_template.md`.

## 7. Long-Term Memory Mandate

- **Mandate**: You are explicitly required to update `docs/AI_INSIGHTS.md` whenever you encounter a project-specific nuance, recurring pitfall, or architectural constraint.
- **Trigger**: If you find yourself thinking "I should remember this for next time" or "This was unexpected," you MUST document it in `docs/AI_INSIGHTS.md`.
