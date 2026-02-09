"""
Shared ChromaDB client pool.

Wraps nebulus-core's VectorClient to provide a single ChromaDB client
instance reused across all services. Falls back to direct chromadb
creation if nebulus-core is unavailable.
"""

import logging
from typing import Optional

import chromadb

from backend.platform import get_chroma_settings

logger = logging.getLogger(__name__)

_vector_client: Optional[object] = None
_raw_client: Optional[chromadb.ClientAPI] = None
_initialized = False


def get_chroma_client() -> Optional[chromadb.ClientAPI]:
    """Get the shared ChromaDB client, creating it on first call.

    Tries nebulus-core's VectorClient first, falls back to direct
    chromadb creation. Returns the raw chromadb client for backward
    compatibility with MemoryService and DocumentService.
    """
    global _vector_client, _raw_client, _initialized

    if _initialized:
        return _raw_client

    _initialized = True
    settings = get_chroma_settings()

    try:
        from nebulus_core.vector import VectorClient

        _vector_client = VectorClient(settings)
        _raw_client = _vector_client.client  # type: ignore[union-attr]
        logger.info(f"ChromaDB connected via VectorClient (mode={settings.get('mode')})")
    except Exception:
        try:
            if settings.get("mode") == "embedded":
                _raw_client = chromadb.PersistentClient(path=settings["path"])
            else:
                _raw_client = chromadb.HttpClient(
                    host=settings.get("host", "localhost"),
                    port=settings.get("port", 8001),
                )
            logger.info(f"ChromaDB connected directly (mode={settings.get('mode')})")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable: {e}")
            _raw_client = None

    return _raw_client


def get_vector_client() -> Optional[object]:
    """Get the nebulus-core VectorClient for higher-level operations.

    Returns None if nebulus-core is unavailable (use get_chroma_client()
    for the raw client fallback).
    """
    if not _initialized:
        get_chroma_client()
    return _vector_client


def close_chroma_client() -> None:
    """Close the shared ChromaDB client. Call on application shutdown."""
    global _vector_client, _raw_client, _initialized
    if _raw_client is not None:
        try:
            if hasattr(_raw_client, "_session"):
                _raw_client._session.close()
        except Exception:
            pass
        _raw_client = None
    _vector_client = None
    _initialized = False
    logger.info("ChromaDB shared client closed")
