# Nebulus Gantry Regression Test Plan

**Version:** 1.0
**Status:** DRAFT
**Scope:** Functional Parity (Black Box) & Architectural Compliance (White Box)

## 1. Executive Summary

This test plan defines the strategy to validate the "Modernization Refactor" of Nebulus Gantry. The refactor transformed a monolithic Python/Spaghetti JS codebase into a strictly layered architecture (Service Layer Backend + ES6 MVC Frontend).

**Core Objective:** Prove that the new architecture behaves identically to the old one (Functional Parity) while strictly checking that no legacy patterns remain (Compliance).

## 2. High-Risk Areas

The following areas underwent the most significant structural changes and require the highest coverage density:

| Feature Area | Risk | Primary Test Type | Description |
| :--- | :--- | :--- | :--- |
| **User Authentication** | Critical | Integration | Auth logic moved to `AuthService`. Middleware changes. |
| **Notes Synchronization** | High | Unit (JS) & Integration | Complex state management in `Notes.js` refactored to `NoteService` + Frontend Store. |
| **Chat History / Sidebar** | High | Integration | Data flow from `ChatRouter` to `Sidebar` component. Real-time updates. |
| **Search Functionality** | Medium | Unit (JS) | New `Search` component class logic and API interaction. |

## 3. Testing Strategy

### 3.1 Backend Regression (Python/Pytest)

**Goal:** Verify Service Layer isolation and Route schema compliance.

* **Service Layer Tests (`tests/services/`)**:
  * **Isolation:** MUST mock database sessions and external calls (MCP, OpenAI).
  * **Logic:** verify business rules (e.g., "Notes must have a default category if none provided").
  * **Error Handling:** Ensure Services raise custom Exceptions, not generic Failures.

* **Route Integration Tests (`tests/routers/`)**:
  * **Schema Validation:** Assert responses match Pydantic Models (JSON), not SQL Alchemy objects.
  * **Status Codes:** Verify Service Exception map to correct HTTP 4xx/5xx codes.
  * **Dependency Injection:** Verify `get_db` and `get_current_user` can be overridden for tests.

### 3.2 Frontend Regression (Jest/Vitest)

**Goal:** Verify ES6 Class encapsulation and Global Store integrity.

* **Component Unit Tests (`src/js/components/*.test.js`)**:
  * **Instantiation:** `new Component()` should not throw.
  * **Rendering:** `render()` should affect the DOM correctly based on `props`.
  * **Event Handling:** Mock DOM events and assert expected method calls.

* **State Store Tests (`src/js/core/store.test.js`)**:
  * **Immutability:** State updates should create new references (if enforced) or correctly modify properties.
  * **Pub/Sub:** Subscribers must be notified upon `setState`.

### 3.3 Structural & Semantic Validation (Linting/Static Analysis)

**Goal:** Fail the build if legacy anti-patterns are checked in.

* **HTML Semantics:**
  * Clickable elements must be `<button>` or `<a>`.
  * Forms must have associated `<label>`s.
* **CSS Architecture (BEM):**
  * Class names must match `block__element--modifier` or utility patterns.
  * No inline styles allowed in JS logic (use class toggling).
* **Codebase Hygiene:**
  * **Forbidden:** `document.querySelector` inside Route logic (Wait, this is backend, impossible, but conceptually separate concerns).
  * **Forbidden:** `SELECT * FROM` strings in Routers (Must use ORM).
  * **Forbidden:** Global variables in JS (Must use `Nebulus` namespace).

## 4. Test Environment Requirements

* **Python:** `pytest`, `pytest-asyncio`, `pytest-mock`, `httpx`.
* **JavaScript:** `jest` (with `jsdom` environment).
* **Data:** In-memory SQLite DB for backend tests.

## 5. Acceptance Criteria

1. All Critical/High-risk features pass Functional Parity tests.
2. Backend Code Coverage > 80% on Service Layer.
3. Anti-Pattern Scanner reports 0 violations.
