"""Platform bridge — single source of truth for service URLs.

Lazily attempts to load nebulus-core's PlatformAdapter for configuration.
Falls back to environment variables, then hardcoded defaults. Never crashes
if nebulus-core or the adapter is unavailable.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_adapter: Optional[object] = None
_adapter_loaded = False


def _load_adapter() -> Optional[object]:
    """Attempt to load the platform adapter once."""
    global _adapter, _adapter_loaded
    if _adapter_loaded:
        return _adapter
    _adapter_loaded = True
    try:
        from nebulus_core.platform import detect_platform, load_adapter

        platform = detect_platform()
        _adapter = load_adapter(platform)
        logger.info(f"Loaded nebulus-core adapter: {platform}")
    except Exception as e:
        logger.debug(f"nebulus-core adapter unavailable: {e}")
        _adapter = None
    return _adapter


def get_llm_base_url() -> str:
    """Return the LLM endpoint URL (without /v1 suffix).

    Gantry services append /v1/... themselves, so this must return
    only the scheme+host+port (e.g. http://localhost:8080).

    Priority: NEBULUS_LLM_URL → TABBY_HOST (backward compat) →
              adapter.llm_base_url → default.
    """
    env = os.getenv("NEBULUS_LLM_URL") or os.getenv("TABBY_HOST")
    if env:
        return env.rstrip("/").removesuffix("/v1")
    adapter = _load_adapter()
    if adapter is not None:
        try:
            url = adapter.llm_base_url  # type: ignore[union-attr]
            return url.rstrip("/").removesuffix("/v1")
        except Exception:
            pass
    return "http://localhost:5000"


def get_chroma_settings() -> dict:
    """Return ChromaDB connection config dict.

    Priority: NEBULUS_CHROMA_URL → CHROMA_HOST (backward compat) →
              adapter.chroma_settings → default.

    Returns:
        {"mode": "http", "host": str, "port": int} or
        {"mode": "embedded", "path": str}
    """
    env = os.getenv("NEBULUS_CHROMA_URL") or os.getenv("CHROMA_HOST")
    if env:
        url = env
        if url.startswith("http://"):
            url = url[7:]
        elif url.startswith("https://"):
            url = url[8:]
        if ":" in url:
            host, port_str = url.split(":", 1)
            return {"mode": "http", "host": host, "port": int(port_str)}
        return {"mode": "http", "host": url, "port": 8000}
    adapter = _load_adapter()
    if adapter is not None:
        try:
            return adapter.chroma_settings  # type: ignore[union-attr]
        except Exception:
            pass
    return {"mode": "http", "host": "localhost", "port": 8001}


def get_default_model() -> str:
    """Return the default LLM model name.

    Priority: NEBULUS_DEFAULT_MODEL → adapter.default_model → "default".
    """
    env = os.getenv("NEBULUS_DEFAULT_MODEL")
    if env:
        return env
    adapter = _load_adapter()
    if adapter is not None:
        try:
            return adapter.default_model  # type: ignore[union-attr]
        except Exception:
            pass
    return "default"


def get_platform_name() -> str:
    """Return the platform adapter name (e.g. 'prime', 'edge') or 'unknown'."""
    adapter = _load_adapter()
    if adapter is not None:
        try:
            return adapter.platform_name  # type: ignore[union-attr]
        except Exception:
            pass
    return "unknown"


def get_service_manager_type() -> str:
    """Return the service management backend type.

    Returns 'docker' if Docker is available, 'pm2' if the adapter
    indicates PM2 (e.g. Edge/macOS), or 'none'.
    """
    try:
        import docker
        docker.from_env()
        return "docker"
    except Exception:
        pass
    adapter = _load_adapter()
    if adapter is not None:
        try:
            return adapter.service_manager_type  # type: ignore[union-attr]
        except Exception:
            pass
    return "none"


def get_mcp_settings() -> dict | None:
    """Return MCP server config from adapter, or None if unavailable."""
    adapter = _load_adapter()
    if adapter is not None:
        try:
            return adapter.mcp_settings  # type: ignore[union-attr]
        except Exception:
            pass
    return None
