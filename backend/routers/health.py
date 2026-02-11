"""Health check endpoints for monitoring and load balancers.

Provides /api/health (detailed status) and /api/health/ready (k8s readiness probe).
No authentication required.
"""

import time

import httpx
from fastapi import APIRouter, Response
from pydantic import BaseModel

from backend.config import settings
from backend.platform import get_chroma_settings, get_llm_base_url

router = APIRouter(prefix="/api/health", tags=["health"])

_start_time: float = time.monotonic()

VERSION = "0.1.0-mva"


class HealthResponse(BaseModel):
    """Full health check response."""

    status: str
    version: str
    mode: str
    llm_url: str
    llm_reachable: bool
    services: dict[str, str]
    uptime_seconds: float


class ReadyResponse(BaseModel):
    """Readiness probe response."""

    ready: bool


def _check_llm_reachable(llm_url: str) -> bool:
    """Check if the LLM endpoint is reachable with a 2s timeout."""
    try:
        resp = httpx.get(f"{llm_url}/health", timeout=2.0)
        return resp.status_code < 500
    except Exception:
        return False


def _check_chromadb_reachable() -> bool:
    """Check if ChromaDB is reachable with a 2s timeout."""
    chroma = get_chroma_settings()
    if chroma.get("mode") == "embedded":
        return True
    host = chroma.get("host", "localhost")
    port = chroma.get("port", 8000)
    try:
        resp = httpx.get(f"http://{host}:{port}/api/v1/heartbeat", timeout=2.0)
        return resp.status_code < 500
    except Exception:
        return False


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    """Full health check with service status."""
    llm_url = get_llm_base_url()
    llm_reachable = _check_llm_reachable(llm_url)
    chromadb_reachable = _check_chromadb_reachable()

    services = {
        "llm": "ok" if llm_reachable else "unreachable",
        "chromadb": "ok" if chromadb_reachable else "unreachable",
    }

    all_ok = llm_reachable and chromadb_reachable
    mode = "overlord" if settings.overlord_routing_enabled else "standalone"

    return HealthResponse(
        status="ok" if all_ok else "degraded",
        version=VERSION,
        mode=mode,
        llm_url=llm_url,
        llm_reachable=llm_reachable,
        services=services,
        uptime_seconds=round(time.monotonic() - _start_time, 2),
    )


@router.get("/ready", response_model=ReadyResponse)
def readiness(response: Response) -> ReadyResponse:
    """Kubernetes-style readiness probe. Returns 503 if LLM is unreachable."""
    llm_url = get_llm_base_url()
    reachable = _check_llm_reachable(llm_url)
    if not reachable:
        response.status_code = 503
    return ReadyResponse(ready=reachable)
