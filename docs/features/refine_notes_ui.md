# Feature: Notes UI Refinement

## 1. Goal
Ensure the "Notes" section is fully styled and consistent with the application's premium aesthetic by implementing missing CSS classes and refining existing ones.

## 2. Issues Identified
- **Missing Button Classes**: `ui/pages.py` uses `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger` but these are not defined in `style.css`.
- **Missing Component Classes**: `.notes-toolbar` and `.note-category-input` are structured in HTML but lack CSS definitions.
- **Utility Gaps**: `notes.js` uses `.text-accent`, `.pl-5`, `.font-medium` which may be missing or inconsistent.

## 3. Implementation Plan
### [MODIFY] `public/style.css`
- **Button System**:
  - Define `.btn` (base styles: padding, radius, transition, cursor).
  - Define `.btn-primary` (Accent color background).
  - Define `.btn-secondary` (Background hover/secondary).
  - Define `.btn-danger` / `.btn-danger-outline` (Red styling).
- **Notes Specific**:
  - `.notes-toolbar`: Flexbox layout, border-bottom?
  - `.note-category-input`: Transparent, smaller font than title, secondary color.
- **Utilities**:
  - `.text-accent` (Gradient or Accent Color).
  - `.pl-5` (Padding Left).
  - `.font-medium` (Font Weight 500).

## 4. Verification
- **Visual Check**:
  - Buttons should look clickable and "premium" (not default browser buttons).
  - Toolbar should be aligned.
  - Inputs should blend into the editor (not look like standard input boxes).
