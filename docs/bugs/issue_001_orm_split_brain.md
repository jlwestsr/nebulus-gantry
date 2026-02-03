# Bug Report: Split-Brain ORM Configuration Causing Language Server Recursion

**Date:** 2026-01-26
**Status:** Resolved (2026-02-03) — Legacy src/nebulus_gantry/ directory deleted. v2 backend/ is the sole source of truth.
**Severity:** High (Dev Tooling Stability) / Medium (Runtime Risk)

## Description

The Pyrefly Language Server crashes repeatedly with a `stack overflow` error when analyzing the codebase. This is caused by a circular dependency and "split-brain" definition of SQLAlchemy ORM models.

## Root Cause

There are two redundant definitions of the database models (entities):

1. **Legacy:** `src/nebulus_gantry/database.py`
2. **New Backend:** `src/nebulus_gantry/backend/models/entities.py`

Both files define `User`, `Chat`, `Message`, etc., mapped to the same database tables.

- `src/nebulus_gantry/main.py` imports from the **Legacy** definitions.
- `src/nebulus_gantry/backend/dependencies.py` mixes imports (Getting session from New DB config, but importing User model from Legacy).

This ambiguity causes static analysis tools (and potentially runtime mappers) to enter infinite recursion loops trying to resolve the types.

## Affected Components

- **Language Server:** Crashes on file open/save.
- **Runtime:** Potential for `Class 'X' is already mapped to table 'Y'` errors if both modules are fully loaded and used in the same session context for writes.

## Proposed Fix

Consolidate all database logic to the new `backend/` directory structure.

1. **Migrate Logic:** Move `migrate_db` and `init_db` logic from `src/nebulus_gantry/database.py` to `src/nebulus_gantry/backend/database.py`.
2. **Update Imports:** Refactor `main.py` and `dependencies.py` to strictly import from `nebulus_gantry.backend.models.entities` and `nebulus_gantry.backend.database`.
3. **Cleanup:** Delete the legacy file `src/nebulus_gantry/database.py`.

## reproduction

Open `tests/routers/test_admin_rbac.py` or any file importing `User` in VSCode with the Pyrefly extension enabled.
