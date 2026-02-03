"""
Tests for the Memory Service (ChromaDB integration).

Tests cover:
- Embedding messages and storing in ChromaDB
- Searching for similar messages
- Graceful degradation when ChromaDB is unavailable
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture
def mock_chroma_collection():
    """Create a mock ChromaDB collection."""
    collection = MagicMock()
    collection.add = MagicMock()
    collection.query = MagicMock(return_value={
        "ids": [["msg_1", "msg_2"]],
        "documents": [["Hello there", "How are you"]],
        "distances": [[0.1, 0.3]],
        "metadatas": [[
            {"conversation_id": 1, "role": "user", "timestamp": "2024-01-01T00:00:00"},
            {"conversation_id": 1, "role": "assistant", "timestamp": "2024-01-01T00:01:00"}
        ]]
    })
    return collection


@pytest.fixture
def mock_chroma_client(mock_chroma_collection):
    """Create a mock ChromaDB HTTP client."""
    client = MagicMock()
    client.get_or_create_collection = MagicMock(return_value=mock_chroma_collection)
    return client


class TestMemoryServiceInit:
    """Tests for MemoryService initialization."""

    def test_init_creates_user_collection(self, mock_chroma_client, mock_chroma_collection):
        """Test that initialization creates a user-specific collection."""
        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)

            mock_chroma_client.get_or_create_collection.assert_called_once_with(
                name="user_42_messages"
            )
            assert service.collection == mock_chroma_collection

    def test_init_handles_connection_failure(self):
        """Test graceful handling when ChromaDB is unavailable at init."""
        with patch("chromadb.HttpClient", side_effect=Exception("Connection refused")):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)

            assert service.collection is None
            assert service.available is False


class TestEmbedMessage:
    """Tests for the embed_message method."""

    @pytest.mark.asyncio
    async def test_embed_message_stores_correctly(self, mock_chroma_client, mock_chroma_collection):
        """Test that embed_message stores content in ChromaDB."""
        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            await service.embed_message(
                message_id=123,
                content="Hello, how can I help you?",
                metadata={"conversation_id": 1, "role": "user"}
            )

            mock_chroma_collection.add.assert_called_once_with(
                ids=["msg_123"],
                documents=["Hello, how can I help you?"],
                metadatas=[{"conversation_id": 1, "role": "user"}]
            )

    @pytest.mark.asyncio
    async def test_embed_message_with_no_metadata(self, mock_chroma_client, mock_chroma_collection):
        """Test embed_message works without metadata."""
        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            await service.embed_message(message_id=456, content="Test message")

            mock_chroma_collection.add.assert_called_once_with(
                ids=["msg_456"],
                documents=["Test message"],
                metadatas=[{}]
            )

    @pytest.mark.asyncio
    async def test_embed_message_when_unavailable(self):
        """Test embed_message returns gracefully when ChromaDB unavailable."""
        with patch("chromadb.HttpClient", side_effect=Exception("Connection refused")):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            # Should not raise an exception
            result = await service.embed_message(message_id=123, content="Test")

            assert result is None

    @pytest.mark.asyncio
    async def test_embed_message_handles_runtime_error(self, mock_chroma_client, mock_chroma_collection):
        """Test embed_message handles errors during storage."""
        mock_chroma_collection.add.side_effect = Exception("Storage error")

        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            # Should not raise, just log and return None
            result = await service.embed_message(message_id=123, content="Test")

            assert result is None


class TestSearchSimilar:
    """Tests for the search_similar method."""

    @pytest.mark.asyncio
    async def test_search_similar_returns_results(self, mock_chroma_client, mock_chroma_collection):
        """Test that search_similar returns properly formatted results."""
        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            results = await service.search_similar("Hello", limit=5)

            mock_chroma_collection.query.assert_called_once_with(
                query_texts=["Hello"],
                n_results=5
            )

            assert len(results) == 2
            assert results[0]["content"] == "Hello there"
            assert results[0]["score"] == 0.1
            assert results[0]["metadata"]["conversation_id"] == 1
            assert results[1]["content"] == "How are you"
            assert results[1]["score"] == 0.3

    @pytest.mark.asyncio
    async def test_search_similar_respects_limit(self, mock_chroma_client, mock_chroma_collection):
        """Test that search_similar passes limit to ChromaDB."""
        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            await service.search_similar("test query", limit=10)

            mock_chroma_collection.query.assert_called_once_with(
                query_texts=["test query"],
                n_results=10
            )

    @pytest.mark.asyncio
    async def test_search_similar_default_limit(self, mock_chroma_client, mock_chroma_collection):
        """Test that search_similar uses default limit of 5."""
        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            await service.search_similar("test query")

            mock_chroma_collection.query.assert_called_once_with(
                query_texts=["test query"],
                n_results=5
            )

    @pytest.mark.asyncio
    async def test_search_similar_when_unavailable(self):
        """Test search_similar returns empty list when ChromaDB unavailable."""
        with patch("chromadb.HttpClient", side_effect=Exception("Connection refused")):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            results = await service.search_similar("test query")

            assert results == []

    @pytest.mark.asyncio
    async def test_search_similar_handles_runtime_error(self, mock_chroma_client, mock_chroma_collection):
        """Test search_similar handles errors during query."""
        mock_chroma_collection.query.side_effect = Exception("Query error")

        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            results = await service.search_similar("test query")

            assert results == []

    @pytest.mark.asyncio
    async def test_search_similar_handles_empty_results(self, mock_chroma_client, mock_chroma_collection):
        """Test search_similar handles empty query results."""
        mock_chroma_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "distances": [[]],
            "metadatas": [[]]
        }

        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            results = await service.search_similar("nonexistent query")

            assert results == []


class TestMemoryServiceAvailability:
    """Tests for the availability property."""

    def test_available_when_connected(self, mock_chroma_client, mock_chroma_collection):
        """Test that available is True when ChromaDB is connected."""
        with patch("chromadb.HttpClient", return_value=mock_chroma_client):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            assert service.available is True

    def test_not_available_when_disconnected(self):
        """Test that available is False when ChromaDB is unavailable."""
        with patch("chromadb.HttpClient", side_effect=Exception("Connection refused")):
            from backend.services.memory_service import MemoryService

            service = MemoryService(user_id=42)
            assert service.available is False
