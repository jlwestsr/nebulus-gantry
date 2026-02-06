# Claude Code Project Configuration

Project-specific plugin and tooling configuration for Nebulus Gantry.

## Plugin Configuration

This directory contains `.claude/config.json` which configures Claude Code plugins **specifically for this project**.

### Enabled Plugins (High Priority)

**Language Support:**

- ✅ **Pyright LSP** - Python type checking for FastAPI backend
- ✅ **TypeScript LSP** - TypeScript analysis for React frontend

**Development Tools:**

- ✅ **GitHub** - PR/issue management, CI status
- ✅ **Playwright** - UI testing automation
- ✅ **Serena** - Semantic code navigation
- ✅ **Superpowers** - Brainstorming, TDD, debugging

**Workflow Helpers:**

- ✅ **PR Review Toolkit** - Automated code reviews
- ✅ **Commit Commands** - Git workflow automation
- ✅ **Feature Dev** - Feature development workflows
- ✅ **Context7** - Live documentation lookup
- ✅ **Security Guidance** - Production security checks

### Disabled Plugins

- ❌ **Supabase** - Not using Supabase (using SQLite/PostgreSQL)
- ❌ **Ralph Loop** - No automation loops in current workflow

## LSP Configuration

### Python (Pyright)

Configuration: `pyrightconfig.json` (project root)

**Settings:**

- Type checking: basic
- Python version: 3.12
- Include: `backend/`
- Exclude: `__pycache__`, `.pytest_cache`, `node_modules`
- Virtual environment: `./venv`

**What it checks:**

- Type hint correctness
- Missing imports
- Function signature mismatches
- Optional/None handling

### TypeScript

Configuration: `frontend/tsconfig.json` + project references

**Settings:**

- React 19 support
- Vite build tool
- Auto-imports enabled
- Strict mode

**What it checks:**

- TypeScript type errors
- React prop types
- Component interfaces
- Import resolution

## Per-Project vs Global

**This is a per-project configuration** - it only applies when working in this directory.

Other projects in the `west_ai_labs` workspace can have different plugin configurations:

- `nebulus-core/` might enable different plugins
- `nebulus-prime/` might have different priorities
- `nebulus-edge/` might use different LSP settings

## Updating Configuration

**To enable/disable a plugin:**

Edit `.claude/config.json`:

```json
{
  "mcpServers": {
    "plugin-name": {
      "disabled": false,  // true to disable
      "priority": "high",  // high, medium, low
      "reason": "Why this plugin is needed"
    }
  }
}
```

**To update LSP settings:**

- Python: Edit `pyrightconfig.json`
- TypeScript: Edit `frontend/tsconfig.json`

## Testing Plugin Configuration

**Check which plugins are active:**

```bash
# Claude Code will log active plugins in startup
# Look for "Loading MCP server: plugin-name"
```

**Verify LSP is working:**

1. Open `backend/main.py`
2. Hover over a type hint - should show documentation
3. CMD/Ctrl+Click on an import - should navigate to definition

**Test GitHub integration:**

```bash
# In Claude Code, ask:
# "What's the status of PR #123?"
# "Create a PR for this branch"
```

## Why Per-Project?

**Benefits:**

- ✅ Different projects have different needs
- ✅ Lighter weight (only load what's needed)
- ✅ Faster startup (fewer plugins to initialize)
- ✅ Team consistency (config is version controlled)
- ✅ Easy to share (commit `.claude/` to repo)

**Example:**

- Gantry (this project): Heavy on Python/TypeScript LSP, GitHub, Playwright
- Nebulus Core (library): Heavy on Python LSP, lighter on UI tools
- Nebulus Edge (macOS): Different deployment plugins

## Troubleshooting

**Plugin not working:**

1. Check `.claude/config.json` - is it disabled?
2. Restart Claude Code
3. Check logs for "Failed to load MCP server"

**LSP not providing suggestions:**

1. Check `pyrightconfig.json` or `tsconfig.json`
2. Ensure virtual environment is activated
3. Check for syntax errors in config files

**Too many plugins slowing down:**

1. Set low-priority plugins to `"disabled": true`
2. Keep only essential plugins enabled
3. Monitor startup time

## Version Control

**Should this be committed?**

✅ **YES - Commit `.claude/config.json`**

- Team members get same plugin setup
- Consistent development experience
- Documents recommended tools

❌ **NO - Don't commit `.claude/cache/`**

- Plugin cache files
- User-specific data
- Add to `.gitignore`

## Documentation

See project documentation for more:

- [AI_DIRECTIVES.md](../AI_DIRECTIVES.md) - AI agent rules
- [AI_INSIGHTS.md](../docs/AI_INSIGHTS.md) - Project learnings
- [WORKFLOW.md](../WORKFLOW.md) - Development workflow

---

*Last updated: 2026-02-06*
