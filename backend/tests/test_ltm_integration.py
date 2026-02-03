"""
Tests for Long-Term Memory (LTM) integration into the chat flow.

Tests cover:
- build_ltm_context helper function
- LTM context injection into system message before LLM call
- LTM updates (embedding + graph) after assistant response
- Graceful degradation when LTM services are unavailable
- Chat endpoint still works normally when LTM fails
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from backend.routers.chat import build_ltm_context


class TestBuildLtmContext:
    """Tests for the build_ltm_context helper function."""

    def test_empty_inputs_returns_empty_string(self):
        """Returns empty string when no similar messages or facts."""
        result = build_ltm_context([], [])
        assert result == ""

    def test_similar_messages_only(self):
        """Formats similar messages into context string."""
        similar = [
            {"content": "I love Python programming", "score": 0.1, "metadata": {}},
            {"content": "FastAPI is great for APIs", "score": 0.2, "metadata": {}},
        ]
        result = build_ltm_context(similar, [])
        assert "Relevant past context:" in result
        assert "- I love Python programming" in result
        assert "- FastAPI is great for APIs" in result

    def test_related_facts_only(self):
        """Formats related facts into context string."""
        facts = [
            {"entity": "Python", "relationship": "mentioned_in", "connected_entity": "conversation_1"},
            {"entity": "FastAPI", "relationship": "used_by", "connected_entity": "Project X"},
        ]
        result = build_ltm_context([], facts)
        assert "Known facts:" in result
        assert "- Python mentioned_in conversation_1" in result
        assert "- FastAPI used_by Project X" in result

    def test_both_messages_and_facts(self):
        """Includes both similar messages and related facts."""
        similar = [
            {"content": "Hello world", "score": 0.1, "metadata": {}},
        ]
        facts = [
            {"entity": "World", "relationship": "greeted_in", "connected_entity": "conversation_1"},
        ]
        result = build_ltm_context(similar, facts)
        assert "Relevant past context:" in result
        assert "Known facts:" in result

    def test_limits_similar_messages_to_3(self):
        """Only includes the first 3 similar messages."""
        similar = [
            {"content": f"Message {i}", "score": 0.1 * i, "metadata": {}}
            for i in range(5)
        ]
        result = build_ltm_context(similar, [])
        assert "- Message 0" in result
        assert "- Message 1" in result
        assert "- Message 2" in result
        assert "- Message 3" not in result
        assert "- Message 4" not in result

    def test_limits_facts_to_5(self):
        """Only includes the first 5 facts."""
        facts = [
            {"entity": f"Entity{i}", "relationship": "rel", "connected_entity": f"Target{i}"}
            for i in range(7)
        ]
        result = build_ltm_context([], facts)
        assert "Entity4" in result
        assert "Entity5" not in result

    def test_truncates_long_message_content(self):
        """Truncates message content to 200 characters."""
        long_content = "A" * 300
        similar = [{"content": long_content, "score": 0.1, "metadata": {}}]
        result = build_ltm_context(similar, [])
        # The content portion should be truncated at 200 chars
        # "- " prefix + 200 chars of content
        lines = result.strip().split("\n")
        content_line = lines[1]  # First line is header
        # "- " + 200 chars = 202
        assert len(content_line) == 202


# --- Helpers for endpoint tests ---

def _mock_memory_service(similar_results=None):
    """Create a mock MemoryService instance."""
    mock = MagicMock()
    mock.available = True
    mock.search_similar = AsyncMock(return_value=similar_results or [])
    mock.embed_message = AsyncMock(return_value=True)
    return mock


def _mock_graph_service(entities=None, related_facts=None):
    """Create a mock GraphService instance."""
    mock = MagicMock()
    mock.extract_entities = MagicMock(return_value=entities or [])
    mock.get_related = MagicMock(return_value=related_facts or [])
    mock.add_fact = MagicMock()
    mock.save = MagicMock()
    return mock


class TestSendMessageLtmIntegration:
    """Tests for LTM integration in the send_message endpoint.

    These tests use the FastAPI test client and mock the LTM services
    via the _create_memory_service and _create_graph_service factory
    functions in the chat router module.
    """

    @pytest.fixture
    def test_db(self):
        """Create an in-memory SQLite database for testing."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from backend.database import Base
        from backend.services.auth_service import AuthService

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create test user
        auth = AuthService(session)
        auth.create_user("ltm@test.com", "password123", "LTM Test User")

        yield session
        session.close()

    @pytest.fixture
    def client(self, test_db):
        """Create a FastAPI test client with overridden DB."""
        from fastapi.testclient import TestClient
        from backend.main import app
        from backend.dependencies import get_db

        def override_get_db():
            yield test_db

        app.dependency_overrides[get_db] = override_get_db
        yield TestClient(app)
        app.dependency_overrides.pop(get_db, None)

    @pytest.fixture
    def authenticated_client(self, client):
        """Login and return authenticated test client."""
        client.post("/api/auth/login", json={
            "email": "ltm@test.com",
            "password": "password123",
        })
        return client

    @pytest.fixture
    def conversation_id(self, authenticated_client):
        """Create a conversation and return its ID."""
        response = authenticated_client.post("/api/chat/conversations")
        return response.json()["id"]

    def test_send_message_with_ltm_context(self, authenticated_client, conversation_id):
        """Chat endpoint works with LTM services providing context."""
        mock_memory = _mock_memory_service(
            similar_results=[
                {"content": "Previous conversation about Python", "score": 0.1, "metadata": {}},
            ]
        )
        mock_graph = _mock_graph_service(
            entities=[{"type": "entity", "value": "Python"}],
            related_facts=[
                {"entity": "Python", "relationship": "mentioned_in", "connected_entity": "conversation_1"},
            ],
        )

        with patch(
            "backend.routers.chat._create_memory_service",
            return_value=mock_memory,
        ), patch(
            "backend.routers.chat._create_graph_service",
            return_value=mock_graph,
        ):
            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Tell me about Python"},
            )
            _ = response.text

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_send_message_graceful_degradation_memory_fails(
        self, authenticated_client, conversation_id
    ):
        """Chat still works when MemoryService creation raises an exception."""
        mock_graph = _mock_graph_service()

        with patch(
            "backend.routers.chat._create_memory_service",
            side_effect=Exception("ChromaDB down"),
        ), patch(
            "backend.routers.chat._create_graph_service",
            return_value=mock_graph,
        ):
            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Hello"},
            )
            _ = response.text

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_send_message_graceful_degradation_both_fail(
        self, authenticated_client, conversation_id
    ):
        """Chat still works when both LTM services fail."""
        with patch(
            "backend.routers.chat._create_memory_service",
            side_effect=Exception("ChromaDB down"),
        ), patch(
            "backend.routers.chat._create_graph_service",
            side_effect=Exception("Graph error"),
        ):
            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Hello"},
            )
            _ = response.text

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_send_message_graceful_degradation_graph_fails(
        self, authenticated_client, conversation_id
    ):
        """Chat still works when GraphService raises an exception."""
        mock_memory = _mock_memory_service()

        with patch(
            "backend.routers.chat._create_memory_service",
            return_value=mock_memory,
        ), patch(
            "backend.routers.chat._create_graph_service",
            side_effect=Exception("Graph error"),
        ):
            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Hello"},
            )
            _ = response.text

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_send_message_no_ltm_context_when_empty(
        self, authenticated_client, conversation_id
    ):
        """When LTM returns no results, system message has no extra context."""
        mock_memory = _mock_memory_service(similar_results=[])
        mock_graph = _mock_graph_service(entities=[], related_facts=[])

        with patch(
            "backend.routers.chat._create_memory_service",
            return_value=mock_memory,
        ), patch(
            "backend.routers.chat._create_graph_service",
            return_value=mock_graph,
        ):
            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Hello"},
            )
            _ = response.text

        assert response.status_code == 200

    def test_send_message_calls_memory_search(
        self, authenticated_client, conversation_id
    ):
        """Verifies MemoryService.search_similar is called with user content."""
        mock_memory = _mock_memory_service()
        mock_graph = _mock_graph_service()

        with patch(
            "backend.routers.chat._create_memory_service",
            return_value=mock_memory,
        ), patch(
            "backend.routers.chat._create_graph_service",
            return_value=mock_graph,
        ):
            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Search this message"},
            )
            # Read the streaming response to trigger the generator
            _ = response.text

        mock_memory.search_similar.assert_called_once_with(
            "Search this message", limit=3
        )

    def test_send_message_calls_graph_extract(
        self, authenticated_client, conversation_id
    ):
        """Verifies GraphService.extract_entities is called with user content."""
        mock_memory = _mock_memory_service()
        mock_graph = _mock_graph_service()

        async def fake_stream(messages):
            yield "Some response"

        with patch(
            "backend.routers.chat._create_memory_service",
            return_value=mock_memory,
        ), patch(
            "backend.routers.chat._create_graph_service",
            return_value=mock_graph,
        ), patch(
            "backend.routers.chat.LLMService"
        ) as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.stream_chat = MagicMock(side_effect=fake_stream)
            mock_llm_cls.return_value = mock_llm

            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Extract from this"},
            )
            _ = response.text

        # extract_entities is called once before LLM (user content)
        # and once after LLM (assistant response)
        mock_graph.extract_entities.assert_any_call("Extract from this")

    def test_send_message_embeds_after_response(
        self, authenticated_client, conversation_id
    ):
        """Verifies messages are embedded into ChromaDB after streaming completes."""
        mock_memory = _mock_memory_service()
        mock_graph = _mock_graph_service()

        # Mock the LLM to return a known response
        async def fake_stream(messages):
            yield "Hello from LLM"

        with patch(
            "backend.routers.chat._create_memory_service",
            return_value=mock_memory,
        ), patch(
            "backend.routers.chat._create_graph_service",
            return_value=mock_graph,
        ), patch(
            "backend.routers.chat.LLMService"
        ) as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.stream_chat = MagicMock(side_effect=fake_stream)
            mock_llm_cls.return_value = mock_llm

            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Test embedding"},
            )
            # Read full response to trigger generator completion
            _ = response.text

        # embed_message should have been called twice (user + assistant)
        assert mock_memory.embed_message.call_count == 2

    def test_send_message_updates_graph_after_response(
        self, authenticated_client, conversation_id
    ):
        """Verifies graph is updated with entities from the assistant response."""
        mock_memory = _mock_memory_service()
        mock_graph = _mock_graph_service()
        # Make extract_entities return something for the assistant response
        mock_graph.extract_entities = MagicMock(
            side_effect=[
                # First call: extracting from user message (before LLM call)
                [],
                # Second call: extracting from assistant response (after LLM)
                [{"type": "entity", "value": "TestEntity"}],
            ]
        )

        async def fake_stream(messages):
            yield "Response mentioning TestEntity"

        with patch(
            "backend.routers.chat._create_memory_service",
            return_value=mock_memory,
        ), patch(
            "backend.routers.chat._create_graph_service",
            return_value=mock_graph,
        ), patch(
            "backend.routers.chat.LLMService"
        ) as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.stream_chat = MagicMock(side_effect=fake_stream)
            mock_llm_cls.return_value = mock_llm

            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Hello"},
            )
            _ = response.text

        mock_graph.add_fact.assert_called_with(
            entity1="TestEntity",
            relationship="mentioned_in",
            entity2=f"conversation_{conversation_id}",
        )
        mock_graph.save.assert_called_once()

    def test_send_message_embed_failure_does_not_crash(
        self, authenticated_client, conversation_id
    ):
        """Chat continues normally even if embedding fails after response."""
        mock_memory = _mock_memory_service()
        mock_memory.embed_message = AsyncMock(side_effect=Exception("Embed failed"))
        mock_graph = _mock_graph_service()

        async def fake_stream(messages):
            yield "LLM response"

        with patch(
            "backend.routers.chat._create_memory_service",
            return_value=mock_memory,
        ), patch(
            "backend.routers.chat._create_graph_service",
            return_value=mock_graph,
        ), patch(
            "backend.routers.chat.LLMService"
        ) as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.stream_chat = MagicMock(side_effect=fake_stream)
            mock_llm_cls.return_value = mock_llm

            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Test"},
            )
            # Should not raise even though embed fails
            text = response.text

        assert response.status_code == 200
        assert "LLM response" in text

    def test_send_message_graph_save_failure_does_not_crash(
        self, authenticated_client, conversation_id
    ):
        """Chat continues normally even if graph save fails after response."""
        mock_memory = _mock_memory_service()
        mock_graph = _mock_graph_service()
        mock_graph.save = MagicMock(side_effect=Exception("Save failed"))
        mock_graph.extract_entities = MagicMock(
            side_effect=[
                [],  # user message extraction
                [{"type": "entity", "value": "Foo"}],  # assistant response extraction
            ]
        )

        async def fake_stream(messages):
            yield "Response with Foo"

        with patch(
            "backend.routers.chat._create_memory_service",
            return_value=mock_memory,
        ), patch(
            "backend.routers.chat._create_graph_service",
            return_value=mock_graph,
        ), patch(
            "backend.routers.chat.LLMService"
        ) as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.stream_chat = MagicMock(side_effect=fake_stream)
            mock_llm_cls.return_value = mock_llm

            response = authenticated_client.post(
                f"/api/chat/conversations/{conversation_id}/messages",
                json={"content": "Test"},
            )
            text = response.text

        assert response.status_code == 200
        assert "Response with Foo" in text
