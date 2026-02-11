#!/usr/bin/env python3
"""
E2E Smoke Test for Nebulus Gantry Appliance

Validates the full appliance flow end-to-end:
  1. Health check (GET /health)
  2. User creation via admin API (POST /api/admin/users)
  3. Login (POST /api/auth/login)
  4. Verify "Dealership Analyst" persona exists (GET /api/personas)
  5. Create conversation (POST /api/chat/conversations)
  6. Send message via SSE streaming (POST /api/chat/conversations/{id}/messages)
  7. Verify non-empty assistant response received
  8. Cleanup (optional, delete test conversation)

Prerequisites:
  - Gantry backend must be running and accessible
  - An admin user must exist for test user creation (or the test user
    must already exist from a previous run)
  - LLM inference server must be available for the message send step

Environment Variables:
  GANTRY_URL        Base URL of the Gantry backend (default: http://localhost:8000)
  ADMIN_EMAIL       Admin email for creating the test user (default: admin@nebulus.local)
  ADMIN_PASSWORD    Admin password (default: admin)
  TEST_EMAIL        Test user email (default: smoketest@nebulus.local)
  TEST_PASSWORD     Test user password (default: smoketest123)

Usage:
  # Run against local development backend
  python tests/e2e_smoke_test.py

  # Run against a specific host (e.g., Mac Mini appliance)
  GANTRY_URL=http://192.168.1.50:8000 python tests/e2e_smoke_test.py

  # Run with custom admin credentials
  ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=secret python tests/e2e_smoke_test.py

Designed to run on both dev (Linux) and appliance (macOS) environments.
Exit code 0 on success, 1 on failure.
"""

import json
import os
import sys
import time

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.getenv("GANTRY_URL", "http://localhost:8000").rstrip("/")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@nebulus.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
TEST_EMAIL = os.getenv("TEST_EMAIL", "smoketest@nebulus.local")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "smoketest123")
TEST_DISPLAY_NAME = "Smoke Test User"

TIMEOUT = 15  # seconds per request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SmokeTestFailure(Exception):
    """Raised when a smoke test step fails."""


def result(label: str, passed: bool, detail: str = "") -> None:
    """Print a pass/fail line for a test step."""
    tag = "[PASS]" if passed else "[FAIL]"
    msg = f"  {tag} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def api(method: str, path: str, session: requests.Session | None = None,
        json_data: dict | None = None, stream: bool = False) -> requests.Response:
    """Make an API request with consistent error handling."""
    url = f"{BASE_URL}{path}"
    http = session or requests
    try:
        resp = http.request(method, url, json=json_data, timeout=TIMEOUT, stream=stream)
        return resp
    except requests.ConnectionError:
        raise SmokeTestFailure(
            f"Connection refused: {url}\n"
            f"       Is the Gantry backend running at {BASE_URL}?"
        )
    except requests.Timeout:
        raise SmokeTestFailure(f"Request timed out after {TIMEOUT}s: {method} {url}")


# ---------------------------------------------------------------------------
# Test Steps
# ---------------------------------------------------------------------------

def step_health_check() -> None:
    """Step 1: Verify the backend is alive."""
    resp = api("GET", "/health")
    if resp.status_code != 200:
        raise SmokeTestFailure(f"Health check returned {resp.status_code}")
    body = resp.json()
    if body.get("status") != "healthy":
        raise SmokeTestFailure(f"Unexpected health response: {body}")
    result("Health Check", True)


def step_create_test_user(session: requests.Session) -> None:
    """Step 2: Create a test user via the admin API.

    Requires an admin session. Tolerates 409 (user already exists).
    If admin auth fails, attempts direct login with test credentials
    (user may already exist from a previous run).
    """
    # First, authenticate as admin
    resp = api("POST", "/api/auth/login", session=session, json_data={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })

    if resp.status_code == 200:
        # Create the test user via admin endpoint
        resp = api("POST", "/api/admin/users", session=session, json_data={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "display_name": TEST_DISPLAY_NAME,
            "role": "user",
        })
        if resp.status_code == 201:
            result("Create Test User", True, "created via admin API")
            return
        elif resp.status_code == 409:
            result("Create Test User", True, "already exists (409)")
            return
        else:
            raise SmokeTestFailure(
                f"Admin user creation returned {resp.status_code}: {resp.text}"
            )

    # Admin login failed — the test user may already exist from a
    # previous run.  We'll verify at the login step.
    result("Create Test User", True, "skipped (no admin access, will verify at login)")


def step_login(session: requests.Session) -> None:
    """Step 3: Log in as the test user and extract session cookie."""
    # Log out any existing session first
    api("POST", "/api/auth/logout", session=session)

    resp = api("POST", "/api/auth/login", session=session, json_data={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    if resp.status_code != 200:
        raise SmokeTestFailure(
            f"Login failed ({resp.status_code}): {resp.text}\n"
            f"       Ensure the test user '{TEST_EMAIL}' exists."
        )
    # Verify session cookie was set
    if "session_token" not in session.cookies:
        raise SmokeTestFailure("Login succeeded but no session_token cookie received")
    result("Login", True)


def step_verify_persona(session: requests.Session) -> None:
    """Step 4: Verify the 'Dealership Analyst' persona exists."""
    resp = api("GET", "/api/personas", session=session)
    if resp.status_code != 200:
        raise SmokeTestFailure(f"List personas returned {resp.status_code}: {resp.text}")
    personas = resp.json()
    names = [p.get("name", "") for p in personas]
    if "Dealership Analyst" not in names:
        raise SmokeTestFailure(
            f"'Dealership Analyst' persona not found. Available: {names}"
        )
    result("Dealership Analyst Persona", True, f"{len(personas)} persona(s) available")


def step_create_conversation(session: requests.Session) -> int:
    """Step 5: Create a new conversation. Returns the conversation ID."""
    resp = api("POST", "/api/chat/conversations", session=session)
    if resp.status_code != 200:
        raise SmokeTestFailure(
            f"Create conversation returned {resp.status_code}: {resp.text}"
        )
    data = resp.json()
    conv_id = data.get("id")
    if not conv_id:
        raise SmokeTestFailure(f"Conversation response missing 'id': {data}")
    result("Create Conversation", True, f"id={conv_id}")
    return conv_id


def step_send_message(session: requests.Session, conversation_id: int) -> str:
    """Step 6: Send a message and read the SSE streaming response.

    Returns the full assistant response text.
    """
    resp = api(
        "POST",
        f"/api/chat/conversations/{conversation_id}/messages",
        session=session,
        json_data={"content": "Hello, what can you help me with?"},
        stream=True,
    )
    if resp.status_code != 200:
        raise SmokeTestFailure(
            f"Send message returned {resp.status_code}: {resp.text}"
        )

    # Read the SSE stream — the backend yields raw text chunks
    # (not data:-prefixed SSE lines) via StreamingResponse
    full_response = ""
    for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
        if chunk:
            full_response += chunk

    # Strip metadata suffix if present (format: \n\n__META__{json})
    meta_marker = "\n\n__META__"
    if meta_marker in full_response:
        text_part, meta_json = full_response.rsplit(meta_marker, 1)
        full_response = text_part
        try:
            meta = json.loads(meta_json)
            gen_time = meta.get("generation_time_ms", "?")
            tokens = meta.get("total_tokens", "?")
            result("Send Message (SSE)", True,
                   f"{len(full_response)} chars, {gen_time}ms, {tokens} tokens")
        except json.JSONDecodeError:
            result("Send Message (SSE)", True, f"{len(full_response)} chars (meta parse error)")
    else:
        result("Send Message (SSE)", True, f"{len(full_response)} chars")

    return full_response


def step_verify_response(response_text: str) -> None:
    """Step 7: Verify the assistant response is non-empty and reasonable."""
    stripped = response_text.strip()
    if not stripped:
        raise SmokeTestFailure("Assistant response was empty")
    if len(stripped) < 5:
        raise SmokeTestFailure(
            f"Assistant response suspiciously short ({len(stripped)} chars): {stripped!r}"
        )
    result("Verify Response", True, f"{len(stripped)} chars, starts with: {stripped[:80]!r}")


def step_cleanup(session: requests.Session, conversation_id: int) -> None:
    """Step 8: Clean up the test conversation (best-effort)."""
    try:
        resp = api("DELETE", f"/api/chat/conversations/{conversation_id}", session=session)
        if resp.status_code == 200:
            result("Cleanup", True, f"deleted conversation {conversation_id}")
        else:
            result("Cleanup", True, f"skipped (status {resp.status_code})")
    except Exception:
        result("Cleanup", True, "skipped (error)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Run all smoke test steps. Returns 0 on success, 1 on failure."""
    print("\nNebulus Gantry E2E Smoke Test")
    print(f"Target: {BASE_URL}")
    print(f"Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    session = requests.Session()
    conversation_id = None

    try:
        step_health_check()
        step_create_test_user(session)
        step_login(session)
        step_verify_persona(session)
        conversation_id = step_create_conversation(session)
        response_text = step_send_message(session, conversation_id)
        step_verify_response(response_text)
        step_cleanup(session, conversation_id)

        print("-" * 50)
        print("  RESULT: ALL CHECKS PASSED")
        print()
        return 0

    except SmokeTestFailure as e:
        print(f"\n  [FAIL] {e}")
        print("-" * 50)
        print("  RESULT: SMOKE TEST FAILED")
        print()
        # Best-effort cleanup
        if conversation_id:
            step_cleanup(session, conversation_id)
        return 1

    except Exception as e:
        print(f"\n  [ERROR] Unexpected error: {e}")
        print("-" * 50)
        print("  RESULT: SMOKE TEST ERROR")
        print()
        return 1

    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
