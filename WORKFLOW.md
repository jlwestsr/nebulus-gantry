# Development Workflow for Nebulus Gantry

## 1. Overview

This document defines the collaboration protocol between the human user and the AI agent for developing **Nebulus Gantry**. The AI agent operates as a full engineering partner, not a passive assistant.

## 2. Core Philosophy

- **Agent as Engineer**: You are the standard for this project. Own your work.
- **Git-Ops Centric**: All changes flow through Git branches (`feat/`, `fix/`, etc.).
- **Reference-Driven**: Decisions are based on existing patterns in `backend/` and `frontend/src/`, not general knowledge.

## 3. Branching Strategy

Gantry uses a simplified branch model with `main` as the single permanent branch.

### Permanent Branch (Remote)

- **`main`**: Production-ready code. All work merges here.

### Temporary Branches (Local Only)

**CRITICAL**: These branches exist **only** on your local machine. Do **not** push them to origin unless working on a long-lived collaborative feature.

- **`feat/name`**: New features (components, services, endpoints)
- **`fix/description`**: Bug fixes
- **`docs/description`**: Documentation updates
- **`chore/description`**: Maintenance, config, refactoring

## 4. The Agentic Workflow Cycle

### Phase 1: Discovery & Audit

**Trigger**: User requests a new feature or reports a bug.

**Agent Action**:

1. Read `docs/AI_INSIGHTS.md` to recall project caveats.
2. Check existing code and tests in `backend/` and `frontend/src/`.
3. Produce a task breakdown for the work.

### Phase 2: Proposal (The "Green Light")

**Trigger**: Discovery complete.

**Agent Action**:

1. Create an implementation plan.
2. Create a feature spec in `docs/features/` using `docs/feature_template.md` (for significant features).
3. Define the "Why", "What", and "Verification Plan".
4. **Hold**: Await explicit user approval before proceeding.

### Phase 3: Implementation

**Trigger**: User approves the plan.

**Agent Action**:

1. Create a feature branch from `main`.
2. Write code following patterns in `CONTEXT.md` and `AI_DIRECTIVES.md`.
3. Write tests in `backend/tests/`.
4. Verify locally with `pytest` and `bin/gantry validate`.

### Phase 4: Delivery (The "Deploy")

**Trigger**: Verification passes.

**Agent Action**:

1. Commit changes using conventional commit messages.
2. Merge to `main` locally.
3. Update `docs/AI_INSIGHTS.md` if any new lessons were learned.
4. Notify user: "Feature complete. Tests passed."

## 5. Execution Steps (Standard Operating Procedure)

### Step 1 — Start

Checkout `main` and pull latest.

```bash
git checkout main
git pull origin main
```

### Step 2 — Branch

Create a specific local branch.

```bash
git checkout -b feat/my-new-feature
```

### Step 3 — Work

Implement changes using conventional commits.

```bash
git add <files>
git commit -m "feat: add new feature"
```

### Step 4 — Verify

Run tests and validation to ensure stability.

```bash
bin/gantry validate
# or individually:
cd backend && python -m pytest tests/ -v
pre-commit run --all-files
```

### Step 5 — Merge

Switch back to `main` and merge.

```bash
git checkout main
git merge feat/my-new-feature
```

### Step 6 — Push

Push **only** with explicit user authorization.

```bash
git push origin main
```

### Step 7 — Cleanup

Delete the local branch.

```bash
git branch -d feat/my-new-feature
```

## 6. Docker Development Workflow

```bash
# Start the full stack
bin/gantry start

# Stop the stack
bin/gantry stop

# Rebuild after dependency changes
bin/gantry rebuild

# View logs
bin/gantry logs

# Check container status
bin/gantry status

# Run validation
bin/gantry validate
```

Docker volumes mount source directories for hot-reload during development. Backend changes are picked up by `--reload` flag on uvicorn. Frontend changes are picked up by Vite HMR.

## 7. Parallel Development (Git Worktrees)

For working on multiple features simultaneously, use git worktrees:

```bash
# Create a worktree for a feature
git worktree add .worktrees/feat-name feat/feature-name

# List active worktrees
git worktree list

# Remove when done
git worktree remove .worktrees/feat-name
```

The `.worktrees/` directory is gitignored. Each worktree gets its own working directory with independent checkout.

## 8. GitHub CLI (`gh`) Usage

```bash
# Issues
gh issue list
gh issue create --title "Bug: ..." --body "..."

# Pull Requests
gh pr create --title "feat: ..." --body "..."
gh pr list
gh pr merge <number>

# CI/CD
gh run list
gh run view <id>
```

## 9. Security & Safety

- **No Auto-Merge**: Never merge to `main` without explicit user command.
- **No Secrets in Commits**: Never commit `.env` files, API keys, or credentials.
- **Verification First**: Always run tests before declaring work complete.
- **Push Authorization**: Never push to remote without explicit user approval.
