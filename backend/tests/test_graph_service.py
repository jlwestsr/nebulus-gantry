"""
Tests for the Graph Service (NetworkX-based associative memory).

Tests cover:
- Entity extraction from message content
- Adding facts/relationships to the graph
- Querying related entities
- Persistence (save/load)
"""
import json
import os
import tempfile
import pytest
from unittest.mock import patch

import backend.services.graph_service as graph_service_module
from backend.services.graph_service import GraphService


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory and patch DATA_DIR to use it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_data_dir = graph_service_module.DATA_DIR
        graph_service_module.DATA_DIR = tmpdir
        yield tmpdir
        graph_service_module.DATA_DIR = original_data_dir


class TestGraphServiceInit:
    """Tests for GraphService initialization."""

    def test_init_creates_empty_graph_for_new_user(self, temp_data_dir):
        """Test that initialization creates an empty graph for new user."""
        service = GraphService(user_id=42)

        assert service.graph is not None
        assert service.graph.number_of_nodes() == 0
        assert service.graph.number_of_edges() == 0

    def test_init_loads_existing_graph(self, temp_data_dir):
        """Test that initialization loads existing graph from file."""
        # Create a graph file using the current NetworkX node_link format
        graph_data = {
            "directed": True,
            "multigraph": False,
            "graph": {},
            "nodes": [
                {"id": "Alice", "type": "person"},
                {"id": "Project X", "type": "project"}
            ],
            "edges": [
                {"source": "Alice", "target": "Project X", "relationship": "works_on"}
            ]
        }
        graph_file = os.path.join(temp_data_dir, "user_42_graph.json")
        with open(graph_file, "w") as f:
            json.dump(graph_data, f)

        service = GraphService(user_id=42)

        assert service.graph.number_of_nodes() == 2
        assert service.graph.number_of_edges() == 1
        assert "Alice" in service.graph.nodes
        assert "Project X" in service.graph.nodes

    def test_init_creates_data_directory_if_missing(self):
        """Test that initialization creates the data directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = os.path.join(tmpdir, "nonexistent_data")
            original_data_dir = graph_service_module.DATA_DIR
            graph_service_module.DATA_DIR = data_dir
            try:
                service = GraphService(user_id=42)
                assert os.path.exists(data_dir)
            finally:
                graph_service_module.DATA_DIR = original_data_dir


class TestExtractEntities:
    """Tests for entity extraction from text."""

    def test_extract_capitalized_words(self, temp_data_dir):
        """Test extraction of capitalized words (potential names/entities)."""
        service = GraphService(user_id=1)
        entities = service.extract_entities(
            "I met with Alice and Bob yesterday to discuss the project."
        )

        entity_values = [e["value"] for e in entities]
        assert "Alice" in entity_values
        assert "Bob" in entity_values

    def test_extract_email_addresses(self, temp_data_dir):
        """Test extraction of email addresses."""
        service = GraphService(user_id=1)
        entities = service.extract_entities(
            "Contact me at john.doe@example.com for more info."
        )

        email_entities = [e for e in entities if e["type"] == "email"]
        assert len(email_entities) == 1
        assert email_entities[0]["value"] == "john.doe@example.com"

    def test_extract_urls(self, temp_data_dir):
        """Test extraction of URLs."""
        service = GraphService(user_id=1)
        entities = service.extract_entities(
            "Check out https://github.com/example/repo for the code."
        )

        url_entities = [e for e in entities if e["type"] == "url"]
        assert len(url_entities) == 1
        assert url_entities[0]["value"] == "https://github.com/example/repo"

    def test_extract_multi_word_entities(self, temp_data_dir):
        """Test extraction of multi-word capitalized entities."""
        service = GraphService(user_id=1)
        entities = service.extract_entities(
            "We are working on Project Alpha with the New York team."
        )

        entity_values = [e["value"] for e in entities]
        # Should capture multi-word entities
        assert "Project Alpha" in entity_values or (
            "Project" in entity_values and "Alpha" in entity_values
        )

    def test_extract_ignores_sentence_start_capitalization(self, temp_data_dir):
        """Test that sentence-starting words aren't always extracted as entities."""
        service = GraphService(user_id=1)
        entities = service.extract_entities(
            "The meeting was great. It went well."
        )

        # Common words at sentence start shouldn't be entities
        entity_values = [e["value"] for e in entities]
        assert "The" not in entity_values
        assert "It" not in entity_values

    def test_extract_empty_string(self, temp_data_dir):
        """Test that empty string returns empty list."""
        service = GraphService(user_id=1)
        entities = service.extract_entities("")

        assert entities == []


class TestAddFact:
    """Tests for adding facts/relationships."""

    def test_add_fact_creates_nodes_and_edge(self, temp_data_dir):
        """Test that add_fact creates both nodes and edge."""
        service = GraphService(user_id=1)
        service.add_fact("Alice", "works_with", "Bob")

        assert "Alice" in service.graph.nodes
        assert "Bob" in service.graph.nodes
        assert service.graph.has_edge("Alice", "Bob")

    def test_add_fact_stores_relationship_type(self, temp_data_dir):
        """Test that add_fact stores the relationship type on the edge."""
        service = GraphService(user_id=1)
        service.add_fact("Alice", "manages", "Project X")

        edge_data = service.graph.get_edge_data("Alice", "Project X")
        assert edge_data["relationship"] == "manages"

    def test_add_fact_with_metadata(self, temp_data_dir):
        """Test that add_fact stores metadata on the edge."""
        service = GraphService(user_id=1)
        service.add_fact(
            "Alice", "emailed", "Bob",
            metadata={"timestamp": "2024-01-01", "subject": "Hello"}
        )

        edge_data = service.graph.get_edge_data("Alice", "Bob")
        assert edge_data["timestamp"] == "2024-01-01"
        assert edge_data["subject"] == "Hello"

    def test_add_fact_multiple_relationships(self, temp_data_dir):
        """Test adding multiple facts between same entities updates edge."""
        service = GraphService(user_id=1)
        service.add_fact("Alice", "knows", "Bob")
        service.add_fact("Alice", "works_with", "Bob")

        # Should have edge (latest relationship wins or stored as list)
        assert service.graph.has_edge("Alice", "Bob")


class TestGetRelated:
    """Tests for querying related entities."""

    def test_get_related_returns_direct_connections(self, temp_data_dir):
        """Test that get_related returns directly connected entities."""
        service = GraphService(user_id=1)
        service.add_fact("Alice", "knows", "Bob")
        service.add_fact("Alice", "knows", "Charlie")

        related = service.get_related("Alice")

        assert len(related) == 2
        connected = [r["connected_entity"] for r in related]
        assert "Bob" in connected
        assert "Charlie" in connected

    def test_get_related_includes_relationship_type(self, temp_data_dir):
        """Test that get_related includes relationship type."""
        service = GraphService(user_id=1)
        service.add_fact("Alice", "manages", "Project X")

        related = service.get_related("Alice")

        assert len(related) == 1
        assert related[0]["relationship"] == "manages"
        assert related[0]["connected_entity"] == "Project X"

    def test_get_related_multi_hop(self, temp_data_dir):
        """Test that get_related can traverse multiple hops."""
        service = GraphService(user_id=1)
        service.add_fact("Alice", "knows", "Bob")
        service.add_fact("Bob", "knows", "Charlie")

        # 1 hop should only get Bob
        related_1hop = service.get_related("Alice", hops=1)
        connected_1hop = [r["connected_entity"] for r in related_1hop]
        assert "Bob" in connected_1hop
        assert "Charlie" not in connected_1hop

        # 2 hops should get both Bob and Charlie
        related_2hop = service.get_related("Alice", hops=2)
        connected_2hop = [r["connected_entity"] for r in related_2hop]
        assert "Bob" in connected_2hop
        assert "Charlie" in connected_2hop

    def test_get_related_returns_incoming_edges(self, temp_data_dir):
        """Test that get_related returns entities that point to the entity."""
        service = GraphService(user_id=1)
        service.add_fact("Bob", "reports_to", "Alice")

        related = service.get_related("Alice")

        # Should find Bob even though Alice doesn't point to Bob
        connected = [r["connected_entity"] for r in related]
        assert "Bob" in connected

    def test_get_related_unknown_entity(self, temp_data_dir):
        """Test that get_related returns empty for unknown entity."""
        service = GraphService(user_id=1)

        related = service.get_related("NonExistent")

        assert related == []


class TestSaveLoad:
    """Tests for persistence (save/load)."""

    def test_save_creates_file(self, temp_data_dir):
        """Test that save creates the graph file."""
        service = GraphService(user_id=42)
        service.add_fact("Alice", "knows", "Bob")
        service.save()

        graph_file = os.path.join(temp_data_dir, "user_42_graph.json")
        assert os.path.exists(graph_file)

    def test_save_persists_graph_data(self, temp_data_dir):
        """Test that saved data can be reloaded."""
        # Create and save a graph
        service1 = GraphService(user_id=42)
        service1.add_fact("Alice", "knows", "Bob")
        service1.add_fact("Alice", "manages", "Project X")
        service1.save()

        # Load in a new instance
        service2 = GraphService(user_id=42)

        assert service2.graph.number_of_nodes() == 3
        assert service2.graph.number_of_edges() == 2
        assert "Alice" in service2.graph.nodes
        assert "Bob" in service2.graph.nodes
        assert "Project X" in service2.graph.nodes

    def test_different_users_have_separate_graphs(self, temp_data_dir):
        """Test that different users have isolated graphs."""
        # User 1's graph
        service1 = GraphService(user_id=1)
        service1.add_fact("Alice", "knows", "Bob")
        service1.save()

        # User 2's graph
        service2 = GraphService(user_id=2)
        service2.add_fact("Charlie", "knows", "Dave")
        service2.save()

        # Reload and verify isolation
        reload1 = GraphService(user_id=1)
        reload2 = GraphService(user_id=2)

        assert "Alice" in reload1.graph.nodes
        assert "Charlie" not in reload1.graph.nodes

        assert "Charlie" in reload2.graph.nodes
        assert "Alice" not in reload2.graph.nodes


class TestEntityTypes:
    """Tests for entity type handling."""

    def test_add_fact_sets_entity_types(self, temp_data_dir):
        """Test that entity types can be set when adding facts."""
        service = GraphService(user_id=1)
        service.add_fact(
            "Alice", "works_on", "Project X",
            metadata={"entity1_type": "person", "entity2_type": "project"}
        )

        assert service.graph.nodes["Alice"].get("type") == "person"
        assert service.graph.nodes["Project X"].get("type") == "project"
