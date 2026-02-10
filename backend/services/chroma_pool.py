"""
Shared ChromaDB client pool.

Wraps nebulus-core's VectorClient to provide a single client instance
reused across all services. Returns None if nebulus-core is unavailable.
"""

import logging
from typing import Optional

from backend.platform import get_chroma_settings

logger = logging.getLogger(__name__)

_vector_client: Optional[object] = None
_initialized = False


def get_vector_client():
    """Get the shared VectorClient, creating it on first call.

    Returns the nebulus-core VectorClient instance, or None if
    nebulus-core is unavailable.
    """
    global _vector_client, _initialized

    if _initialized:
        return _vector_client

    _initialized = True
    settings = get_chroma_settings()

    try:
        from nebulus_core.vector import VectorClient

        _vector_client = VectorClient(settings)
        logger.info(
            f"ChromaDB connected via VectorClient (mode={settings.get('mode')})"
        )
    except Exception as e:
        logger.warning(f"ChromaDB unavailable: {e}")
        _vector_client = None

    return _vector_client


def get_chroma_client():
    """Get the raw ChromaDB client for backward compatibility.

    Returns the underlying chromadb.ClientAPI from VectorClient,
    or None if unavailable.
    """
    vc = get_vector_client()
    if vc is not None:
        return vc.client  # type: ignore[union-attr]
    return None


def close_chroma_client() -> None:
    """Close the shared ChromaDB client. Call on application shutdown."""
    global _vector_client, _initialized
    if _vector_client is not None:
        try:
            raw = _vector_client.client  # type: ignore[union-attr]
            if hasattr(raw, "_session"):
                raw._session.close()
        except Exception:
            pass
        _vector_client = None
    _initialized = False
    logger.info("ChromaDB shared client closed")
