# AI Agent Behavior & Operational Rules

This document outlines the specific operational standards and behavioral expectations for AI agents working on this project.

## 0. Agent Configuration & Rule Hierarchy

When opening a project, the Google Antigravity IDE looks first for rules in the local workspace folder before falling back to global system-wide rules.

### Rule Locations
- **Workspace Rules**: The IDE first checks the project's local directory at `your-workspace/agent/rules/`. It may also load configuration from files like `.cursorrules` or `.antigravity/rules.md` within the workspace root.
- **Global Rules**: If no workspace-specific rules are found, the IDE uses the global rule file at `~/.gemini/GEMINI.md`.

### Directory Structure & Use Cases
| Type | Default File Path | Use Case |
|------|-------------------|----------|
| **Workspace Rule** | `your-workspace/agent/rules/` | Project-specific coding standards or restrictions. |
| **Global Rule** | `~/.gemini/GEMINI.md` | Universal behavior guidelines across all projects. |
| **Workspace Workflow** | `your-workspace/agent/workflows/` | On-demand tasks (e.g., `/generate-unit-tests`). |
| **Global Workflow** | `~/.gemini/antigravity/global_workflows/` | Reusable prompts available in every workspace. |

Rules control the autonomous agent's behavior. They can enforce coding styles or require documentation. The Customizations panel in the IDE's menu allows managing these settings.

## 1. Operational Guardrails
- **Pre-Commit Verification**: Before marking any task as complete, the agent MUST run `pytest` and ensure all tests pass.
- **Linting & Best Practices**: Adhere to strict development best practices for HTML, CSS, JavaScript, and Python.
  - **Compliance**: All code must pass valid linters (`flake8` for Python, `eslint` for JS, `stylelint` for CSS).
  - **Git Hook**: A git hook MUST be configured to validate linting before committing. If it fails, the agent must fix errors immediately.
  - **Structure**: Maintain a clean directory structure with clear separation of concerns.
- **No Shadow Logic**: Do not implement business logic that isn't requested in requirements. If a logic choice is ambiguous, use `notify_user` to clarify.
- **Ansible-First**: Do not run manual `apt install`, `pip install`, or configuration edits unless experimenting. Once confirmed, IMMEDIATELY port the change to an Ansible role.

## 2. Research & Discovery
- **Codebase Awareness**: Before creating a new utility function or module, the agent MUST search `src/` to check for existing implementations.
- **Dependency Check**: Before adding new libraries to `requirements.txt`, the agent must verify if the functionality is already provided by existing dependencies (numpy, pandas, etc.).

## 3. Communication Standards
- **Task Transparency**: Use `TaskSummary` to explain the *why* behind technical decisions, not just the *what*.
- **Plan Approval**: For any change affecting more than 2 files or introducing new architecture, an `implementation_plan.md` must be created and approved via `notify_user`.

## 4. Coding Style (AI-Specific)
- **Type Hinting**: Mandatory for all new functions. Proactively add hints to existing code when modified.
- **Docstring Standard**: Use Google Style docstrings. Include "Args", "Returns", and "Raises" sections where applicable.
- **Refactoring**: When editing a file, small improvements to readability or standards (like removing unused imports) in that file are encouraged.

## 5. Tool Usage
- **Terminal Execution**: Use the terminal to verify file existence and state before making assumptions.
- **Browser Research**: Use the browser tool to look up documentation for specific library versions used in the project.

## 6. Testing & Quality Assurance
- **Mandatory Unit Tests**: All new Python scripts OR significant functional changes to existing ones MUST include unit tests (using `pytest`) in the `tests/` directory.
- **System Verification**: New Ulauncher extensions or major system configurations (desktop entries, services) MUST be added to the `ansible/verify.yml` playbook.
- **Test Runner**: Always run `./scripts/run_tests.sh` before finalizing work to ensure no regressions in linting, unit tests, or system state.
- **Ansible Lint**: While some pre-existing debt exists, all *new* Ansible code should aim for zero legacy warnings. Use specific tasks instead of generic `shell` where possible.
- **Pre-Commit Hook**: A git hook must be used to automatically validate linting (flake8/eslint) and run fast unit tests before commit.
- **Frontend Validation**: Ensure all CSS and JavaScript passes linting (`eslint` / `stylelint`) before deployment or verification.

## 7. Development Workflow
- **Conventional Commits**: Use `feat:`, `fix:`, `docs:`, or `chore:` prefixes.
- **Python Environment**: **MANDATORY**: A local `./venv/` MUST be created and used for all Python operations. System-level Python installation is strictly FORBIDDEN.
- **Node.js**: Use `community.general.npm` with `global: true` for system-wide CLI tools. Ensure `nodejs` and `npm` are installed via `apt` in the `common` role first.
- **Verification**: After applying an Ansible role, run `ansible-playbook ansible/verify.yml` to ensure the system state matches the intended configuration.
- **Security**: Never commit `~/.ssh/` keys or personal tokens. If a script needs to check for them, it should do so without exposing contents.
- **Git Tracking & Branching**:
    - **NO DIRECT WORK ON MAIN/MASTER**. This branch is for production releases only.
    - **Chores**: Minor maintenance or documentation ("chore" work) may be done directly on the `develop` branch.
    - **Features/Bugs**: ALL other work (features, bug fixes, refactors) MUST be done on a new branch (e.g., `feat/...`, `fix/...`) created from `develop`.
    - Always merge `develop` into your feature branch before requesting a merge back.

## 8. Feature Implementation Workflow
When given a directive to work through a feature, follow these steps strictly:
0.  **Create Feature Document**: Create a new file in `docs/features/` using the content from `docs/feature_template.md`. This MUST be the first step to define the feature scope.
1.  **Create a Branch**: Create a new git branch to do the work (e.g., `git checkout -b feat/feature-name`).
2.  **Do the Work**: Implement the changes, following all coding standards and guardrails.
3.  **Test the Work**: Run standard tests (`pytest`, `flake8`) and add new tests as required. Ensure all pass.
4.  **Document the Work**: Update relevant documentation (README, feature docs, walkthrough).
5.  **Commit, Merge, and Push**:
    - Commit changes with conventional messages.
    - Switch to the main development branch (e.g., `develop`).
    - Merge the feature branch.
    - Push the updated branch to the remote.

## 9. Architecture & Frontend Standards
- **Backend Architecture**: All REST API services must be implemented in **Python** (using frameworks like FastAPI or Starlette).
- **Frontend Architecture**: The UI must be JavaScript-driven, interacting with the Python backend REST API for all data requirements. No server-side HTML rendering of dynamic data (return clean skeletons).
- **Separation of Concerns**: Strictly separate structure (HTML), styling (CSS), and logic (JS).
  - **No Inline Styles**: `style="..."` attributes are BANNED in both HTML templates and JavaScript. Use CSS classes toggled via `classList` instead.
- **Technologies**: Use Vanilla JS, HTML, and CSS unless a framework is explicitly requested.
- **Namespacing**: Avoid polluting the global window object. Wrap unrelated logic in a global application object (e.g., `Nebulus.Notes = { ... }`).
- **AJAX**: Use `fetch` (with `async/await`) for all network requests (GET, POST, PUT, DELETE) to the dedicated Python REST API. Ensure robust error handling (try/catch blocks) and loading states.
- **DOM Access**: Use `id` attributes for JavaScript targeting and `class` attributes for styling. Do not mix them.
