# Feature: Project Structure Refactor

## 1. Overview

The goal of this feature is to refactor the `nebulus-gantry` codebase to follow standard software engineering practices by introducing `src/` for source code and `bin/` for executables. This improves organization, usage of Python packages, and separation of concerns.

## 2. Goals

- Create `src/nebulus_gantry/` to house the Python application package.
- Create `bin/` to house executable scripts.
- Ensure Docker containers continue to function correctly.
- Maintain all existing functionality (chat, API, etc.).

## 3. Implementation Details

- **Source Code**: Move all Python files (`.py`) and packages (`routers`, `services`, `exec`, `ops`, `ui`, `metrics`) into `src/nebulus_gantry/`.
- **Executables**: Create `bin/run_app` and `bin/run_tests` to simplify execution.
- **Frontend**: Move `public/` to `src/nebulus_gantry/public` or keep at root. *Decision: Move to `src/nebulus_gantry/public` to keep the package self-contained, or keep at root if it's purely static assets served by uvicorn pointing to a path.*
  - Current `main.py` likely mounts `public`. I should check `main.py`.
- **Configuration**: Update `Dockerfile` to set `ENV PYTHONPATH="${PYTHONPATH}:/app/src"`.

## 4. Verification

- Run `bin/run_tests`.
- Build and run Docker container.
- Manual verification of Web UI.
