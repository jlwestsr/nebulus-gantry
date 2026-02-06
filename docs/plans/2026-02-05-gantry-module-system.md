# Gantry Module System

**Author:** West AI Labs
**Date:** 2026-02-05
**Status:** Draft
**First Consumer:** Nebulus Atom Overlord (see `nebulus-atom/docs/plans/2026-02-05-overlord-design.md`)

---

## 1. Vision

Gantry evolves from a standalone chat application into a **platform** — a host
that discovers, loads, and renders pluggable modules from other Nebulus projects.
The module system follows the same pattern the ecosystem already uses: Python
entry points for discovery, a defined protocol for integration, and clean
separation between host and module.

### Why Modules?

| Without Modules | With Modules |
|----------------|--------------|
| Atom dashboard code lives in Gantry's repo | Atom owns its own UI, ships it as a module |
| Every new feature means editing Gantry's core | New features install without touching Gantry |
| Gantry knows about every project in the ecosystem | Gantry knows about modules; modules know about themselves |
| Tight coupling, merge conflicts, single deploy | Loose coupling, independent releases, composable |

### First Consumer

The Nebulus Atom Overlord will be the first module — providing an ecosystem
dashboard, dispatch console, memory browser, and audit log inside Gantry's
admin panel. This design is informed by that use case but built to be general.

---

## 2. Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                         GANTRY HOST                          │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │  Core UI   │  │  Module    │  │     Frontend Shell     │ │
│  │            │  │  Registry  │  │                        │ │
│  │ • Chat     │  │            │  │ • Route registry       │ │
│  │ • Auth     │  │ • Discover │  │ • Nav menu builder     │ │
│  │ • Settings │  │ • Validate │  │ • Admin tab loader     │ │
│  │ • Admin    │  │ • Register │  │ • Module component map │ │
│  └────────────┘  └─────┬──────┘  └────────────────────────┘ │
│                         │                                    │
├─────────────────────────┼────────────────────────────────────┤
│            Module Protocol (entry points + manifest)         │
├─────────────────────────┼────────────────────────────────────┤
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │              INSTALLED MODULES                        │   │
│  │                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │ Atom        │  │ Forge       │  │ Future      │  │   │
│  │  │ Overlord    │  │ Templates   │  │ Module      │  │   │
│  │  │             │  │             │  │             │  │   │
│  │  │ • router    │  │ • router    │  │ • router    │  │   │
│  │  │ • tabs      │  │ • tabs      │  │ • tabs      │  │   │
│  │  │ • frontend  │  │ • frontend  │  │ • frontend  │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Module Protocol

A Gantry module is a Python package that declares a `gantry.modules` entry
point and provides a **Module Manifest** — a dataclass describing what the
module contributes to the host.

### 3.1 Entry Point Registration

Modules register via `pyproject.toml`:

```toml
# In nebulus-atom/pyproject.toml
[project.entry-points."gantry.modules"]
overlord = "nebulus_atom.gantry:module_manifest"
```

The entry point resolves to a `ModuleManifest` instance.

### 3.2 Module Manifest

```python
from dataclasses import dataclass, field
from typing import Optional
from fastapi import APIRouter


@dataclass
class ModuleNavItem:
    """A top-level navigation entry in Gantry's sidebar."""
    id: str                          # Unique nav identifier
    label: str                       # Display label: "Overlord"
    icon: Optional[str] = None       # Icon name (from shared icon set)
    route: str = ""                  # Frontend route path: "/overlord"
    order: int = 100                 # Sort order (lower = higher in sidebar)
    requires_admin: bool = False     # Admin-only visibility
    frontend_component: str = ""     # Top-level page component name


@dataclass
class ModuleTab:
    """A tab within a module's own page."""
    id: str                          # Unique tab identifier
    label: str                       # Display label
    icon: Optional[str] = None       # Icon name (from shared icon set)
    order: int = 100                 # Sort order (lower = earlier)
    requires_admin: bool = False     # Admin-only visibility
    frontend_component: str = ""     # Component name in the module's frontend bundle


@dataclass
class ModuleManifest:
    """Declares what a module contributes to Gantry."""

    # ─── Identity ───────────────────────────────────────
    name: str                        # Machine name: "overlord", "forge"
    display_name: str                # Human name: "Atom Overlord"
    version: str                     # Semver: "0.1.0"
    description: str                 # Short description

    # ─── Backend ────────────────────────────────────────
    router: Optional[APIRouter] = None   # FastAPI router to mount
    router_prefix: str = ""              # URL prefix: "/api/modules/overlord"

    # ─── Frontend ───────────────────────────────────────
    nav_items: list[ModuleNavItem] = field(default_factory=list)  # Sidebar entries
    tabs: list[ModuleTab] = field(default_factory=list)           # Tabs within module pages
    frontend_bundle: Optional[str] = None   # Path to built JS bundle
    static_dir: Optional[str] = None        # Path to static assets

    # ─── Database ───────────────────────────────────────
    models: list = field(default_factory=list)          # SQLAlchemy models to register
    alembic_version_path: Optional[str] = None          # Path to module's Alembic versions dir

    # ─── Lifecycle ──────────────────────────────────────
    on_startup: Optional[callable] = None    # Called during Gantry startup
    on_shutdown: Optional[callable] = None   # Called during Gantry shutdown
```

### 3.3 Example: Atom Overlord Module

```python
# nebulus_atom/gantry/__init__.py

from nebulus_atom.gantry.router import router
from nebulus_atom.gantry.models import OverlordState, OverlordMemory

module_manifest = ModuleManifest(
    name="overlord",
    display_name="Atom Overlord",
    version="0.1.0",
    description="Cross-project ecosystem orchestrator",
    router=router,
    router_prefix="/api/modules/overlord",

    # Top-level sidebar entry — Overlord gets its own page
    nav_items=[
        ModuleNavItem(
            id="overlord",
            label="Overlord",
            icon="zap",
            route="/overlord",
            order=30,            # After Chat (10), before Settings (40), Admin (50)
            requires_admin=True,
            frontend_component="OverlordPage",
        ),
    ],

    # Tabs within the Overlord page
    tabs=[
        ModuleTab(
            id="ecosystem",
            label="Ecosystem",
            icon="globe",
            order=10,
            requires_admin=True,
            frontend_component="EcosystemDashboard",
        ),
        ModuleTab(
            id="dispatch",
            label="Dispatch",
            icon="send",
            order=11,
            requires_admin=True,
            frontend_component="DispatchConsole",
        ),
        ModuleTab(
            id="memory",
            label="Memory",
            icon="brain",
            order=12,
            requires_admin=True,
            frontend_component="MemoryBrowser",
        ),
        ModuleTab(
            id="audit",
            label="Audit",
            icon="shield",
            order=13,
            requires_admin=True,
            frontend_component="AuditLog",
        ),
    ],
    frontend_bundle="nebulus_atom/gantry/frontend/dist/overlord.js",
    models=[OverlordState, OverlordMemory],
    alembic_version_path="nebulus_atom/gantry/migrations/versions",
    on_startup=lambda: print("Overlord module loaded"),
)
```

---

## 4. Host-Side Changes (Gantry)

### 4.1 Backend: Module Discovery

The module registry discovers and validates all installed modules at startup.

```python
# backend/modules/__init__.py

import importlib.metadata
from typing import list

_registered_modules: list[ModuleManifest] = []


def discover_modules() -> list[ModuleManifest]:
    """Discover all installed Gantry modules via entry points."""
    modules = []
    for ep in importlib.metadata.entry_points(group="gantry.modules"):
        try:
            manifest = ep.load()
            _validate_manifest(manifest)
            modules.append(manifest)
        except Exception as e:
            logger.warning(f"Failed to load module {ep.name}: {e}")
    _registered_modules.extend(modules)
    return modules


def get_registered_modules() -> list[ModuleManifest]:
    """Return all successfully registered modules."""
    return _registered_modules
```

**Integration in `main.py`:**

```python
# backend/main.py — add after core router registration

from backend.modules import discover_modules

# Discover and register module routers
for module in discover_modules():
    if module.router:
        app.include_router(
            module.router,
            prefix=module.router_prefix,
            tags=[f"module:{module.name}"],
        )
    if module.on_startup:
        module.on_startup()

# Module info endpoint
@app.get("/api/modules")
async def list_modules():
    return [
        {
            "name": m.name,
            "display_name": m.display_name,
            "version": m.version,
            "description": m.description,
            "tabs": [
                {
                    "id": t.id,
                    "label": t.label,
                    "icon": t.icon,
                    "section": t.section,
                    "order": t.order,
                    "requires_admin": t.requires_admin,
                    "frontend_component": t.frontend_component,
                }
                for t in m.tabs
            ],
            "frontend_bundle": f"/modules/{m.name}/bundle.js" if m.frontend_bundle else None,
        }
        for m in get_registered_modules()
    ]
```

### 4.2 Backend: Module API Endpoint

A new router that serves module metadata and frontend bundles.

```python
# backend/routers/modules.py

from fastapi import APIRouter
from fastapi.responses import FileResponse
from backend.modules import get_registered_modules

router = APIRouter(prefix="/api/modules", tags=["modules"])


@router.get("/")
async def list_modules():
    """Return metadata for all installed modules."""
    return [_serialize_manifest(m) for m in get_registered_modules()]


@router.get("/{module_name}/bundle.js")
async def get_module_bundle(module_name: str):
    """Serve a module's frontend JavaScript bundle."""
    for m in get_registered_modules():
        if m.name == module_name and m.frontend_bundle:
            return FileResponse(m.frontend_bundle, media_type="application/javascript")
    raise HTTPException(404, f"Module '{module_name}' not found or has no frontend bundle")
```

### 4.3 Frontend: Dynamic Sidebar Navigation

Modules can contribute **top-level sidebar entries** — giving them first-class
visibility alongside Chat, Settings, and Admin. This is the preferred placement
for substantial modules like the Overlord that warrant their own page.

**Decision:** Modules get their own sidebar items and routes, not just admin
tabs. A module like the Overlord is too important to bury inside Admin.

**Before (hardcoded navigation in Layout.tsx):**

```tsx
<Link to="/">Chat</Link>
<Link to="/settings">Settings</Link>
<Link to="/admin">Admin</Link>   {/* admin only */}
```

**After (registry-based):**

```tsx
// frontend/src/hooks/useModules.ts

interface ModuleInfo {
  name: string;
  display_name: string;
  version: string;
  nav_items: ModuleNavItem[];
  tabs: ModuleTab[];
  frontend_bundle: string | null;
}

interface ModuleNavItem {
  id: string;
  label: string;
  icon: string;
  route: string;
  order: number;
  requires_admin: boolean;
  frontend_component: string;
  module_name: string;
  bundle_url: string | null;
}

// Zustand store for module state
export const useModuleStore = create<ModuleState>((set) => ({
  modules: [],
  loaded: false,
  fetchModules: async () => {
    const res = await fetch('/api/modules');
    const modules = await res.json();
    set({ modules, loaded: true });
  },
}));
```

**Layout.tsx evolution — sidebar with module nav items:**

```tsx
// frontend/src/components/Layout.tsx

import { useModuleStore } from '../hooks/useModules';

function Sidebar() {
  const { modules } = useModuleStore();
  const { user } = useAuthStore();

  // Core nav items (always present)
  const coreNav = [
    { label: 'Chat', icon: 'message', route: '/', order: 10 },
    { label: 'Settings', icon: 'settings', route: '/settings', order: 40 },
    ...(user?.role === 'admin'
      ? [{ label: 'Admin', icon: 'shield', route: '/admin', order: 50 }]
      : []),
  ];

  // Module nav items (from installed modules)
  const moduleNav = modules.flatMap(m =>
    m.nav_items
      .filter(n => !n.requires_admin || user?.role === 'admin')
      .map(n => ({ ...n, module_name: m.name, bundle_url: m.frontend_bundle }))
  );

  // Merge and sort
  const allNav = [...coreNav, ...moduleNav].sort((a, b) => a.order - b.order);

  return (
    <nav>
      {allNav.map(item => (
        <NavLink key={item.route} to={item.route}>
          <Icon name={item.icon} />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
```

**App.tsx evolution — dynamic routes for modules:**

```tsx
// frontend/src/App.tsx

import { useModuleStore } from '../hooks/useModules';
import { ModulePageRenderer } from '../components/ModulePageRenderer';

function App() {
  const { modules, loaded, fetchModules } = useModuleStore();

  useEffect(() => { fetchModules(); }, []);

  return (
    <Routes>
      {/* Core routes — always present */}
      <Route path="/" element={<Chat />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/personas" element={<Personas />} />

      {/* Module routes — dynamically registered */}
      {loaded && modules.flatMap(m =>
        m.nav_items.map(nav => (
          <Route
            key={nav.route}
            path={nav.route}
            element={
              <ModulePageRenderer
                moduleName={m.name}
                component={nav.frontend_component}
                bundleUrl={m.frontend_bundle}
                tabs={m.tabs}
              />
            }
          />
        ))
      )}
    </Routes>
  );
}
```

**Result for the Overlord module:**

```text
Sidebar:
  💬 Chat           → /
  ⚡ Overlord       → /overlord     ← Module-contributed
  🔧 Settings       → /settings
  🛡️ Admin          → /admin

/overlord page (module owns this):
  ┌──────────┬──────────┬──────────┬──────────┐
  │Ecosystem │ Dispatch │ Memory   │ Audit    │
  ├──────────┴──────────┴──────────┴──────────┤
  │                                            │
  │         [Active Tab Content]               │
  │                                            │
  └────────────────────────────────────────────┘
```

### 4.4 Frontend: Module Component Loading

Module frontend components need to be loaded dynamically since they don't
exist in Gantry's bundle at build time.

**Approach: Script Injection + Global Registry**

Modules ship pre-built JS bundles. Gantry loads them via `<script>` tag and
reads from a global registry.

```tsx
// frontend/src/components/ModuleTabRenderer.tsx

import { useEffect, useState, useRef } from 'react';

// Global registry where module bundles register their components
declare global {
  interface Window {
    __GANTRY_MODULES__: Record<string, Record<string, React.ComponentType>>;
  }
}
window.__GANTRY_MODULES__ = window.__GANTRY_MODULES__ || {};

interface Props {
  tab: ModuleTab;
}

export function ModuleTabRenderer({ tab }: Props) {
  const [loaded, setLoaded] = useState(false);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

  useEffect(() => {
    // Check if already loaded
    if (window.__GANTRY_MODULES__[tab.module_name]) {
      setLoaded(true);
      return;
    }

    // Load module bundle
    const script = document.createElement('script');
    script.src = tab.bundle_url;
    script.onload = () => setLoaded(true);
    script.onerror = () => console.error(`Failed to load module: ${tab.module_name}`);
    document.head.appendChild(script);
    scriptRef.current = script;

    return () => {
      if (scriptRef.current) document.head.removeChild(scriptRef.current);
    };
  }, [tab.module_name, tab.bundle_url]);

  if (!loaded) return <div>Loading module...</div>;

  const Component = window.__GANTRY_MODULES__[tab.module_name]?.[tab.frontend_component];
  if (!Component) return <div>Component not found: {tab.frontend_component}</div>;

  return <Component />;
}
```

**Module-side bundle registration:**

```tsx
// nebulus_atom/gantry/frontend/src/index.ts

import { EcosystemDashboard } from './EcosystemDashboard';
import { DispatchConsole } from './DispatchConsole';
import { MemoryBrowser } from './MemoryBrowser';
import { AuditLog } from './AuditLog';

// Register components with Gantry's global registry
window.__GANTRY_MODULES__ = window.__GANTRY_MODULES__ || {};
window.__GANTRY_MODULES__['overlord'] = {
  EcosystemDashboard,
  DispatchConsole,
  MemoryBrowser,
  AuditLog,
};
```

---

## 5. Module Development Workflow

### 5.1 Creating a New Module

```bash
# 1. Create the gantry integration package in your project
mkdir -p my_project/gantry/frontend/src

# 2. Define the manifest
cat > my_project/gantry/__init__.py << 'EOF'
from gantry_sdk import ModuleManifest, ModuleTab
from my_project.gantry.router import router

module_manifest = ModuleManifest(
    name="my-module",
    display_name="My Module",
    version="0.1.0",
    description="Does something useful",
    router=router,
    router_prefix="/api/modules/my-module",
    tabs=[
        ModuleTab(id="dashboard", label="Dashboard", section="admin",
                  order=20, frontend_component="Dashboard"),
    ],
    frontend_bundle="my_project/gantry/frontend/dist/my-module.js",
)
EOF

# 3. Register the entry point in pyproject.toml
# [project.entry-points."gantry.modules"]
# my-module = "my_project.gantry:module_manifest"

# 4. Build the frontend bundle
cd my_project/gantry/frontend && npm run build

# 5. Install the package (editable for development)
pip install -e .

# 6. Restart Gantry — module is auto-discovered
bin/gantry rebuild
```

### 5.2 Development Mode

For active development, modules can use Gantry's dev proxy to hot-reload
their frontend components:

```yaml
# docker-compose.override.yml — module dev mode
services:
  atom-module-dev:
    build: ../nebulus-atom/gantry/frontend
    ports: ["3002:3000"]
    volumes:
      - ../nebulus-atom/gantry/frontend/src:/app/src
    command: npm run dev
```

Gantry's frontend can be configured to load module bundles from the dev server
instead of the static bundle:

```bash
VITE_MODULE_OVERLORD_DEV=http://localhost:3002/src/index.ts
```

---

## 6. Shared Resources

### 6.1 Gantry SDK Package

To avoid modules depending on Gantry internals, we publish a lightweight SDK:

```text
gantry-sdk/
├── pyproject.toml
├── gantry_sdk/
│   ├── __init__.py
│   ├── manifest.py      # ModuleManifest, ModuleTab dataclasses
│   ├── auth.py           # require_admin, get_current_user dependencies
│   └── types.py          # Shared Pydantic base schemas
└── frontend/
    └── gantry-sdk.d.ts   # TypeScript types for module authors
```

This package is **tiny** — just dataclasses and FastAPI dependencies. It has
no dependency on Gantry's database, services, or frontend code.

**Module dependency chain:**

```text
gantry-sdk (protocol definitions)
    ↑
nebulus-atom[gantry] (implements the protocol)
    ↑
gantry (discovers and loads modules)
```

### 6.2 Shared UI Components

Modules should look like they belong in Gantry. The SDK provides:

- **TypeScript types** for Gantry's design tokens (colors, spacing, typography)
- **Component stubs** for common patterns (cards, tables, charts, status badges)
- **API client helper** for calling the host's auth-protected endpoints

Modules import Gantry's Tailwind config to stay visually consistent:

```js
// nebulus_atom/gantry/frontend/tailwind.config.js
import gantryPreset from 'gantry-sdk/tailwind-preset';

export default {
  presets: [gantryPreset],
  content: ['./src/**/*.tsx'],
};
```

---

## 7. Security

### 7.1 Module Isolation

- Modules run in the **same Python process** as Gantry's backend (for simplicity).
  They are trusted code installed by the system owner — not untrusted plugins
  from a marketplace.
- Module routers inherit Gantry's auth middleware. The `require_admin` dependency
  from `gantry-sdk` enforces admin-only access where declared.
- Module frontend bundles execute in the **same browser context** as Gantry.
  No iframe sandbox (unnecessary for first-party modules).

### 7.2 Scope

- Modules can only register routes under their declared `router_prefix`
- Modules can declare SQLAlchemy models, but table names must be prefixed
  with the module name (e.g., `overlord_state`, `overlord_memory`)
- Modules cannot modify core Gantry tables or routes

### 7.3 Future: Untrusted Modules

If a module marketplace is ever needed, additional isolation would be required:

- Iframe-sandboxed frontend components
- Separate backend processes with restricted permissions
- Capability-based access to Gantry APIs

This is **out of scope** for the initial implementation. All modules are
first-party Nebulus projects.

---

## 8. Implementation Phases

### Phase 1: Backend Module Discovery + Alembic Migration

**Goal:** Gantry discovers and loads module backend routers at startup. Database
migrations move from ad-hoc to Alembic.

**Alembic adoption** (analogous to Flyway in the JVM world — versioned, sequential
migration scripts with up/down paths and tracked state):

- [ ] `alembic init` in `backend/` — creates `alembic/` directory and `alembic.ini`
- [ ] Write baseline migration representing the current schema as-is
- [ ] `alembic stamp head` on existing databases (marks baseline as applied)
- [ ] Remove ad-hoc migration functions from `backend/dependencies.py`
- [ ] Configure Alembic to discover module migration directories
      (each module can ship its own `versions/` dir via `alembic_version_path`)
- [ ] Add `alembic upgrade head` to Gantry's startup sequence

**Module discovery:**

- [ ] Create `gantry-sdk` package with `ModuleManifest`, `ModuleNavItem`, `ModuleTab`
- [ ] Add `backend/modules/` with entry point discovery logic
- [ ] Add `/api/modules` endpoint (metadata + nav items + tabs)
- [ ] Modify `main.py` to discover and register module routers
- [ ] Write tests for discovery, validation, registration

### Phase 2: Frontend Navigation + Module Pages

**Goal:** Sidebar navigation becomes data-driven. Modules get their own pages
and routes.

- [ ] Refactor `Layout.tsx` sidebar from hardcoded links to registry-based nav
- [ ] Add `useModuleStore` Zustand store for module state
- [ ] Add dynamic `<Route>` generation in `App.tsx` for module pages
- [ ] Add `ModulePageRenderer` component with script injection + tab support
- [ ] Add module bundle serving endpoint (`/api/modules/{name}/bundle.js`)
- [ ] Create a test module to validate the full pipeline end-to-end

### Phase 3: SDK Polish + Dev Experience

**Goal:** Module authors have a clean development workflow.

- [ ] Publish `gantry-sdk` as installable package
- [ ] Add Tailwind preset for visual consistency
- [ ] Add TypeScript type definitions
- [ ] Add `docker-compose.override.yml` pattern for module dev mode
- [ ] Write module authoring guide

### Phase 4: First Module — Atom Overlord

**Goal:** The Overlord module is installed and functional in Gantry.

- [ ] Implement `nebulus_atom/gantry/` package
- [ ] Build Overlord API router (status, dispatch, memory, audit endpoints)
- [ ] Build frontend components (dashboard, dispatch, memory, audit)
- [ ] Test full pipeline: install Atom → restart Gantry → Overlord tabs appear

---

## 9. Relationship to Gantry 1.5 / 2.0

The module system does **not** block or conflict with the current Gantry 1.5
work (Knowledge Vault, Personas). Those features are core Gantry functionality
and stay in the main codebase.

The module system is additive:

| Concern | Where It Lives |
|---------|---------------|
| Chat, auth, settings, personas | **Core Gantry** — always present |
| Knowledge Vault, document management | **Core Gantry** — always present |
| Admin: services, models, logs, users | **Core Gantry** — always present |
| Atom Overlord dashboard | **Module** — present when Atom is installed |
| Forge template browser | **Module** — present when Forge is installed |
| Future ecosystem tools | **Module** — discoverable and composable |

The admin panel refactoring (hardcoded tabs → registry) is a small, focused
change that can land independently and improves the codebase even without
any modules installed.

---

## 10. Resolved Decisions (Gemini Architecture Review)

These decisions were reached through a cross-AI architecture review on 2026-02-05
(Claude as lead architect, Gemini as reviewer).

- **Navigation placement**: **Resolved — top-level sidebar.** Modules can
  contribute their own sidebar entries via `ModuleNavItem`, giving them
  first-class visibility alongside Chat, Settings, and Admin. The Overlord
  gets its own `/overlord` route and page, not a tab buried inside Admin.

- **Alembic**: **Resolved — adopt Alembic in Phase 1.** The ad-hoc migration
  approach doesn't scale to multi-module. Alembic provides versioned, tracked,
  reversible migrations — the same concept as Flyway in the JVM world. Each
  module ships its own `versions/` directory; Gantry's Alembic config discovers
  and runs them all in sequence. Existing databases get a baseline stamp.

- **Bundle format**: **Resolved — ESM (Standard ES Modules).** IIFE is a
  pre-Vite relic. ESM is natively supported by all modern browsers and
  integrates with the existing Vite/TypeScript stack. Modules ship as
  `<script type="module">` bundles.

- **Shared state**: **Resolved — API-only for data, EventBus for UI
  affordances.** Modules must NOT access Gantry's Zustand stores directly —
  that creates hidden coupling. For data (current user, project state), modules
  call API endpoints. For UI actions (toasts, confirmations), the `gantry-sdk`
  provides a typed `EventBus`:

  ```typescript
  // gantry-sdk EventBus API
  gantryEvents.emit('toast', { message: 'Deploy complete', type: 'success' });
  gantryEvents.emit('confirm', { message: 'Push to remote?', onConfirm: fn });
  ```

  Gantry's core subscribes to these events and renders the appropriate UI.
  Type-safe, documented, no direct store access.

- **Dependency isolation**: **Resolved — same-process for now (YAGNI).** All
  first-party modules are Nebulus projects with compatible dependencies. The
  `gantry-sdk` docs will list host library versions (FastAPI, Pydantic, etc.).
  If a real conflict arises in the future, the escape hatch is a sidecar
  pattern: the module runs its own FastAPI service, Gantry proxies to it.

- **CSS collisions**: **Resolved — non-issue with Tailwind.** Utility-first
  CSS prevents global selector collisions. SDK recommends prefixed custom
  classes as a safety convention. No Shadow DOM needed.

## 11. Open Questions

None at this time. All architectural decisions have been resolved.
