#!/usr/bin/env python3
"""E2E smoke test for the Nebulus Gantry MVA appliance.

Validates that all services are up and the critical path
(power on → chat with AI) works end-to-end on the Mac Mini M4 Pro.

Services under test:
    - MLX inference server (port 8080)
    - Gantry FastAPI backend (port 8000)
    - Gantry React frontend (port 3000)
    - ChromaDB (port 8001)
    - Open WebUI (port 3100, optional)

Usage:
    python e2e_smoke_test.py
    python e2e_smoke_test.py --host 192.168.1.50
    python e2e_smoke_test.py --host mac-mini.local --timeout 15
"""

import argparse
import json
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_HOST = "localhost"
DEFAULT_TIMEOUT = 10  # seconds per request

SERVICES = {
    "mlx_inference": {"port": 8080, "path": "/v1/models", "critical": True},
    "gantry_backend": {"port": 8000, "path": "/health", "critical": True},
    "gantry_frontend": {"port": 3000, "path": "/", "critical": True},
    "chromadb": {"port": 8001, "path": "/api/v1/heartbeat", "critical": True},
    "open_webui": {"port": 3100, "path": "/", "critical": False},
}

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Result of a single smoke-test check.

    Attributes:
        name: Human-readable check name.
        passed: Whether the check passed.
        message: Detail string (error info on failure).
        critical: If True, failure means overall test fails.
    """

    name: str
    passed: bool
    message: str = ""
    critical: bool = True


results: list[CheckResult] = []


def _get(url: str, timeout: int) -> tuple[int, str]:
    """Issue a GET request using only stdlib.

    Args:
        url: Full URL to fetch.
        timeout: Socket timeout in seconds.

    Returns:
        Tuple of (status_code, response_body).

    Raises:
        Exception: On network or HTTP errors.
    """
    req = Request(url, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def _post_json(url: str, payload: dict, timeout: int) -> tuple[int, str]:
    """Issue a POST request with a JSON body using only stdlib.

    Args:
        url: Full URL to post to.
        payload: Dict to serialize as JSON body.
        timeout: Socket timeout in seconds.

    Returns:
        Tuple of (status_code, response_body).
    """
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_service_health(host: str, timeout: int) -> None:
    """Check that each service responds on its health endpoint.

    Args:
        host: Hostname or IP of the appliance.
        timeout: Request timeout in seconds.
    """
    for svc_name, cfg in SERVICES.items():
        url = f"http://{host}:{cfg['port']}{cfg['path']}"
        try:
            status, _ = _get(url, timeout)
            ok = 200 <= status < 400
            results.append(CheckResult(
                name=f"health:{svc_name}",
                passed=ok,
                message=f"HTTP {status} from {url}" if not ok else f"OK ({url})",
                critical=cfg["critical"],
            ))
        except Exception as exc:
            results.append(CheckResult(
                name=f"health:{svc_name}",
                passed=False,
                message=f"{url} → {exc}",
                critical=cfg["critical"],
            ))


def check_frontend_content(host: str, timeout: int) -> None:
    """Verify the React frontend serves expected HTML.

    Args:
        host: Hostname or IP of the appliance.
        timeout: Request timeout in seconds.
    """
    url = f"http://{host}:3000/"
    try:
        status, body = _get(url, timeout)
        # The build output from Create-React-App / Vite typically has a <div id="root">
        has_root = "root" in body.lower() or "<html" in body.lower()
        results.append(CheckResult(
            name="frontend:html_content",
            passed=has_root,
            message="Frontend HTML looks valid" if has_root else "Missing expected content in response",
            critical=True,
        ))
    except Exception as exc:
        results.append(CheckResult(
            name="frontend:html_content",
            passed=False,
            message=str(exc),
            critical=True,
        ))


def check_chat_roundtrip(host: str, timeout: int) -> None:
    """Submit a chat message via the Gantry API and verify a response.

    Sends a simple prompt through the backend's chat/completions endpoint
    and checks that the model returns non-empty content.

    Args:
        host: Hostname or IP of the appliance.
        timeout: Request timeout in seconds.
    """
    # Try OpenAI-compatible endpoint first (backend may proxy to MLX)
    endpoints = [
        f"http://{host}:8000/v1/chat/completions",
        f"http://{host}:8000/api/chat",
    ]

    for url in endpoints:
        try:
            payload = {
                "model": "default",
                "messages": [{"role": "user", "content": "Say hello in exactly one word."}],
                "max_tokens": 32,
                "stream": False,
            }
            status, body = _post_json(url, payload, timeout=max(timeout, 30))
            if 200 <= status < 400:
                data = json.loads(body)
                # OpenAI-compatible response
                content = ""
                if "choices" in data:
                    content = data["choices"][0].get("message", {}).get("content", "")
                elif "response" in data:
                    content = data["response"]
                elif "message" in data:
                    content = data.get("message", {}).get("content", "")

                ok = len(content.strip()) > 0
                results.append(CheckResult(
                    name="chat:roundtrip",
                    passed=ok,
                    message=f"Got response: {content[:80]!r}" if ok else "Empty response from model",
                    critical=True,
                ))
                return
        except Exception:
            continue

    # Also try MLX directly as fallback
    try:
        url = f"http://{host}:8080/v1/chat/completions"
        payload = {
            "messages": [{"role": "user", "content": "Say hello in exactly one word."}],
            "max_tokens": 32,
        }
        status, body = _post_json(url, payload, timeout=max(timeout, 30))
        data = json.loads(body)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        ok = len(content.strip()) > 0
        results.append(CheckResult(
            name="chat:roundtrip",
            passed=ok,
            message=f"Got response (direct MLX): {content[:80]!r}" if ok else "Empty response",
            critical=True,
        ))
    except Exception as exc:
        results.append(CheckResult(
            name="chat:roundtrip",
            passed=False,
            message=f"All chat endpoints failed. Last error: {exc}",
            critical=True,
        ))


def check_chromadb_accessible(host: str, timeout: int) -> None:
    """Verify ChromaDB API is reachable and returns collection data.

    Args:
        host: Hostname or IP of the appliance.
        timeout: Request timeout in seconds.
    """
    url = f"http://{host}:8001/api/v1/collections"
    try:
        status, body = _get(url, timeout)
        ok = 200 <= status < 400
        results.append(CheckResult(
            name="chromadb:collections",
            passed=ok,
            message=f"ChromaDB responded with {len(json.loads(body))} collection(s)" if ok else f"HTTP {status}",
            critical=True,
        ))
    except Exception as exc:
        results.append(CheckResult(
            name="chromadb:collections",
            passed=False,
            message=str(exc),
            critical=True,
        ))


def check_outbound_connections() -> None:
    """Informational check for unexpected outbound connections.

    Uses ``ss`` or ``netstat`` to list established outbound connections.
    This check is always non-critical (informational only).
    """
    try:
        out = subprocess.run(
            ["ss", "-tunp", "state", "established"],
            capture_output=True, text=True, timeout=5,
        )
        lines = [l for l in out.stdout.splitlines() if l.strip() and not l.startswith("Netid")]
        # Filter to only non-loopback remote addresses
        external = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                peer = parts[4]
                if not any(peer.startswith(p) for p in ("127.", "[::1]", "0.0.0.0")):
                    external.append(peer)
        msg = f"{len(external)} outbound connection(s)" if external else "No outbound connections detected"
        if external:
            msg += ": " + ", ".join(external[:5])
            if len(external) > 5:
                msg += f" (+{len(external) - 5} more)"
        results.append(CheckResult(
            name="info:outbound_connections",
            passed=True,
            message=msg,
            critical=False,
        ))
    except Exception as exc:
        results.append(CheckResult(
            name="info:outbound_connections",
            passed=True,  # informational, never fails
            message=f"Could not check: {exc}",
            critical=False,
        ))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def print_results() -> bool:
    """Print all results and return True if all critical checks passed.

    Returns:
        True if every critical check passed, False otherwise.
    """
    print("\n" + "=" * 64)
    print("  Nebulus Gantry MVA — E2E Smoke Test Results")
    print("=" * 64)

    all_critical_passed = True
    for r in results:
        tag = "PASS" if r.passed else ("FAIL" if r.critical else "WARN")
        icon = "✅" if r.passed else ("❌" if r.critical else "⚠️")
        crit = " [critical]" if r.critical and not r.passed else ""
        print(f"  {icon} {tag:4s}  {r.name:32s} {r.message}{crit}")
        if r.critical and not r.passed:
            all_critical_passed = False

    print("=" * 64)
    if all_critical_passed:
        print("  ✅ ALL CRITICAL CHECKS PASSED")
    else:
        print("  ❌ SOME CRITICAL CHECKS FAILED")
    print("=" * 64 + "\n")
    return all_critical_passed


def main() -> None:
    """Entry point: parse args and run all smoke-test checks."""
    parser = argparse.ArgumentParser(
        description="E2E smoke test for the Nebulus Gantry MVA appliance.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Appliance hostname or IP (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()

    print(f"\n🔍 Running Nebulus Gantry smoke tests against {args.host} ...")
    start = time.monotonic()

    check_service_health(args.host, args.timeout)
    check_frontend_content(args.host, args.timeout)
    check_chat_roundtrip(args.host, args.timeout)
    check_chromadb_accessible(args.host, args.timeout)
    check_outbound_connections()

    elapsed = time.monotonic() - start
    print(f"\n⏱  Completed in {elapsed:.1f}s")

    ok = print_results()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
