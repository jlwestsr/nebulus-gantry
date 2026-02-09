"""
Shared ChromaDB client pool.

Provides a single HttpClient instance reused across all services,
preventing connection accumulation from per-request client creation.
"""
import logging
from typing import Optional

import chromadb

from backend.config import Settings

logger = logging.getLogger(__name__)

_client: Optional[chromadb.HttpClient] = None
_initialized = False


def _parse_chroma_url(url: str) -> tuple[str, int]:
    """Parse host and port from a ChromaDB URL."""
    if url.startswith("http://"):
        url = url[7:]
    elif url.startswith("https://"):
        url = url[8:]

    if ":" in url:
        host, port_str = url.split(":", 1)
        return host, int(port_str)
    return url, 8000


def get_chroma_client() -> Optional[chromadb.HttpClient]:
    """Get the shared ChromaDB client, creating it on first call."""
    global _client, _initialized

    if _initialized:
        return _client

    _initialized = True
    try:
        settings = Settings()
        host, port = _parse_chroma_url(settings.chroma_host)
        _client = chromadb.HttpClient(host=host, port=port)
        logger.info(f"ChromaDB shared client connected to {host}:{port}")
    except Exception as e:
        logger.warning(f"ChromaDB unavailable: {e}")
        _client = None

    return _client


def close_chroma_client() -> None:
    """Close the shared ChromaDB client. Call on application shutdown."""
    global _client, _initialized
    if _client is not None:
        try:
            _client._session.close()
        except Exception:
            pass
        _client = None
    _initialized = False
    logger.info("ChromaDB shared client closed")
