"""
Memory Service for semantic search using ChromaDB.

Provides:
- Storage of message embeddings
- Retrieval of similar past conversations for context
- Used to augment LLM prompts with relevant history

Graceful degradation: If ChromaDB is unavailable, operations return
empty results without crashing the application.
"""
import logging
from typing import Optional

import chromadb

from backend.config import Settings

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service for managing semantic memory using ChromaDB.

    Each user has their own collection for message storage and retrieval.
    """

    def __init__(self, user_id: int):
        """
        Initialize with user-specific collection.

        Args:
            user_id: The user ID for which to create/access the collection.
        """
        self.user_id = user_id
        self.settings = Settings()
        self.collection = None
        self._available = False

        try:
            # Parse host and port from chroma_host URL
            host_url = self.settings.chroma_host
            # Remove protocol if present
            if host_url.startswith("http://"):
                host_url = host_url[7:]
            elif host_url.startswith("https://"):
                host_url = host_url[8:]

            # Split host and port
            if ":" in host_url:
                host, port_str = host_url.split(":", 1)
                port = int(port_str)
            else:
                host = host_url
                port = 8000

            self.client = chromadb.HttpClient(host=host, port=port)
            self.collection = self.client.get_or_create_collection(
                name=f"user_{user_id}_messages"
            )
            self._available = True
            logger.info(f"ChromaDB connected for user {user_id}")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable: {e}. Memory service will be disabled.")
            self.client = None

    @property
    def available(self) -> bool:
        """Check if the memory service is available."""
        return self._available

    async def embed_message(
        self,
        message_id: int,
        content: str,
        metadata: Optional[dict] = None
    ) -> Optional[bool]:
        """
        Embed a message and store in ChromaDB.

        Args:
            message_id: Unique identifier for the message.
            content: The message content to embed.
            metadata: Optional metadata (conversation_id, role, timestamp, etc.)

        Returns:
            True if successful, None if unavailable or failed.
        """
        if not self.available or self.collection is None:
            return None

        try:
            self.collection.add(
                ids=[f"msg_{message_id}"],
                documents=[content],
                metadatas=[metadata or {}]
            )
            logger.debug(f"Embedded message {message_id} for user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to embed message {message_id}: {e}")
            return None

    async def search_similar(self, query: str, limit: int = 5) -> list[dict]:
        """
        Search for similar past messages.

        Args:
            query: The query text to search for similar messages.
            limit: Maximum number of results to return (default: 5).

        Returns:
            List of dictionaries containing:
                - content: The message content
                - score: Similarity score (distance)
                - metadata: Associated metadata
        """
        if not self.available or self.collection is None:
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )

            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                distances = results["distances"][0] if results.get("distances") else [0] * len(documents)
                metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(documents)

                for i, doc in enumerate(documents):
                    formatted_results.append({
                        "content": doc,
                        "score": distances[i] if i < len(distances) else 0,
                        "metadata": metadatas[i] if i < len(metadatas) else {}
                    })

            return formatted_results
        except Exception as e:
            logger.error(f"Failed to search similar messages: {e}")
            return []
