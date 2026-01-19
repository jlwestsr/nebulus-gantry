# Feature: Workspace UI Refinement

## 1. Goal
Ensure the "Manage Workspaces" section is fully styled, consistent with the "Notes" section, and free of inline styles or duplicate CSS definitions.

## 2. Issues Identified
- **Duplicate Classes**: `.btn-sm` is defined in both `style.css` (globally) and `workspace.css`.
- **Missing Utilities**: `.text-danger` and `.spinner` are used in JS/HTML but missing or undefined.
- **Inline Styles**: `public/workspace.js` uses `style="color:var(--danger)"` for error messages.
- **Consistency**: Modal builder and cards should strictly follow the global `.btn` system.

## 3. Implementation Plan
### [MODIFY] `public/workspace.css`
- Remove `.btn-sm` (use global).
- Consolidate common card styles if possible (or keep specific if unique).

### [MODIFY] `public/style.css`
- Define `.text-danger` (color: #ef4444).
- Define `.spinner` (simple CSS animation).

### [MODIFY] `public/workspace.js`
- Replace `style="color:var(--danger)"` with `class="text-danger"`.
- Ensure spinners use the `.spinner` class correctly.

## 4. Verification
- **Visual Check**:
  - Verify cards look clean.
  - Verify "Pull", "Build", "Refresh" buttons look like standard buttons.
  - Verify error messages (simulate one?) appear red without inline style.
  - Verify loading spinners appear correctly.
