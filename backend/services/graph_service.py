"""
Graph Service for associative memory using NetworkX.

Provides:
- Entity extraction from message content
- Storage of relationships between entities (facts)
- Querying for related entities across multiple hops
- Persistence to user-specific JSON files

Used alongside ChromaDB for comprehensive long-term memory:
- ChromaDB handles semantic similarity search
- GraphService handles structured relationships and facts
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import networkx as nx

logger = logging.getLogger(__name__)

# Data directory for graph storage (can be patched in tests)
DATA_DIR = str(Path(__file__).parent.parent.parent / "data")

# Common words that shouldn't be extracted as entities when at sentence start
COMMON_WORDS = {
    "the", "a", "an", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they",
    "my", "your", "his", "her", "its", "our", "their",
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "must",
    "and", "or", "but", "if", "then", "so", "as", "of", "for", "with",
    "to", "from", "in", "on", "at", "by", "about",
    "what", "when", "where", "why", "how", "who", "which",
    "there", "here", "now", "then", "just", "also", "very",
    "yes", "no", "not", "only", "all", "any", "some", "every",
}


class GraphService:
    """
    Service for managing associative memory using NetworkX graphs.

    Each user has their own graph for storing entity relationships.
    """

    def __init__(self, user_id: int):
        """
        Initialize with user-specific graph.

        Args:
            user_id: The user ID for which to create/access the graph.
        """
        self.user_id = user_id
        self._ensure_data_directory()
        self.graph = self._load_or_create_graph()
        logger.info(f"GraphService initialized for user {user_id}")

    def _ensure_data_directory(self):
        """Create data directory if it doesn't exist."""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            logger.info(f"Created data directory: {DATA_DIR}")

    def _get_graph_path(self) -> str:
        """Get the path to this user's graph file."""
        return os.path.join(DATA_DIR, f"user_{self.user_id}_graph.json")

    def _load_or_create_graph(self) -> nx.DiGraph:
        """Load existing graph from file or create a new one."""
        graph_path = self._get_graph_path()

        if os.path.exists(graph_path):
            try:
                with open(graph_path, "r") as f:
                    data = json.load(f)
                graph = nx.node_link_graph(data)
                logger.info(
                    f"Loaded graph for user {self.user_id}: "
                    f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges"
                )
                return graph
            except Exception as e:
                logger.warning(f"Failed to load graph, creating new: {e}")
                return nx.DiGraph()
        else:
            logger.info(f"Creating new graph for user {self.user_id}")
            return nx.DiGraph()

    def extract_entities(self, content: str) -> list[dict]:
        """
        Extract entities from message content.

        Uses simple heuristics (no external NLP libraries):
        - Capitalized words (2+ chars) not at sentence start
        - Email addresses
        - URLs
        - Multi-word capitalized sequences

        Args:
            content: The message content to extract entities from.

        Returns:
            List of dicts: {type: str, value: str}
        """
        if not content or not content.strip():
            return []

        entities = []
        seen = set()  # Avoid duplicates

        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, content):
            email = match.group()
            if email not in seen:
                entities.append({"type": "email", "value": email})
                seen.add(email)

        # Extract URLs
        url_pattern = r'https?://[^\s<>"\')\]]+(?<![.,;:!?])'
        for match in re.finditer(url_pattern, content):
            url = match.group()
            if url not in seen:
                entities.append({"type": "url", "value": url})
                seen.add(url)

        # Extract capitalized words/phrases (potential names, projects, etc.)
        # Split into sentences first to handle sentence-start capitalization
        sentences = re.split(r'[.!?]+\s*', content)

        for sentence in sentences:
            if not sentence.strip():
                continue

            # Find capitalized words (not at the very start of sentence)
            words = sentence.split()

            # Find multi-word capitalized sequences
            i = 0
            while i < len(words):
                word = words[i]

                # Skip first word unless it's clearly a proper noun pattern
                # (e.g., followed by another capitalized word)
                is_first_word = (i == 0)

                # Clean word of punctuation for checking
                clean_word = re.sub(r'[^\w]', '', word)

                if (
                    len(clean_word) >= 2
                    and clean_word[0].isupper()
                    and clean_word.lower() not in COMMON_WORDS
                ):
                    # Check if this starts a multi-word entity
                    entity_words = [clean_word]
                    j = i + 1

                    while j < len(words):
                        next_word = words[j]
                        next_clean = re.sub(r'[^\w]', '', next_word)
                        if (
                            len(next_clean) >= 2
                            and next_clean[0].isupper()
                            and next_clean.lower() not in COMMON_WORDS
                        ):
                            entity_words.append(next_clean)
                            j += 1
                        else:
                            break

                    # Build entity value
                    if len(entity_words) > 1:
                        # Multi-word entity
                        entity_value = " ".join(entity_words)
                        if entity_value not in seen:
                            entities.append({"type": "entity", "value": entity_value})
                            seen.add(entity_value)
                        i = j
                    elif not is_first_word:
                        # Single capitalized word, not at sentence start
                        if clean_word not in seen:
                            entities.append({"type": "entity", "value": clean_word})
                            seen.add(clean_word)
                        i += 1
                    else:
                        # First word of sentence - only include if clearly a proper noun
                        # (e.g., followed by another cap word)
                        i += 1
                else:
                    i += 1

        return entities

    def add_fact(
        self,
        entity1: str,
        relationship: str,
        entity2: str,
        metadata: Optional[dict] = None
    ):
        """
        Add a relationship to the graph.

        Creates: entity1 -[relationship]-> entity2

        Args:
            entity1: The source entity.
            relationship: The relationship type (edge label).
            entity2: The target entity.
            metadata: Optional dict with additional info. Special keys:
                - entity1_type: Type of entity1 (e.g., "person", "project")
                - entity2_type: Type of entity2
                All other keys are stored as edge attributes.
        """
        metadata = metadata or {}

        # Extract entity types from metadata
        entity1_type = metadata.pop("entity1_type", None)
        entity2_type = metadata.pop("entity2_type", None)

        # Add or update nodes
        if entity1 not in self.graph:
            self.graph.add_node(entity1)
        if entity1_type:
            self.graph.nodes[entity1]["type"] = entity1_type

        if entity2 not in self.graph:
            self.graph.add_node(entity2)
        if entity2_type:
            self.graph.nodes[entity2]["type"] = entity2_type

        # Add edge with relationship and metadata
        edge_attrs = {"relationship": relationship}
        edge_attrs.update(metadata)
        self.graph.add_edge(entity1, entity2, **edge_attrs)

        logger.debug(
            f"Added fact: {entity1} -[{relationship}]-> {entity2}"
        )

    def get_related(self, entity: str, hops: int = 1) -> list[dict]:
        """
        Get entities related to the given entity.

        Args:
            entity: The entity to find relations for.
            hops: Number of relationship hops to traverse (default: 1).

        Returns:
            List of dicts: {entity, relationship, connected_entity}
        """
        if entity not in self.graph:
            return []

        related = []
        visited = {entity}  # Track visited to avoid cycles

        # BFS to find connected entities up to `hops` distance
        current_frontier = [entity]

        for hop in range(hops):
            next_frontier = []

            for current_entity in current_frontier:
                # Get outgoing edges
                for _, target, data in self.graph.out_edges(current_entity, data=True):
                    if target not in visited:
                        visited.add(target)
                        next_frontier.append(target)
                        related.append({
                            "entity": current_entity,
                            "relationship": data.get("relationship", "related_to"),
                            "connected_entity": target
                        })

                # Get incoming edges (bidirectional traversal)
                for source, _, data in self.graph.in_edges(current_entity, data=True):
                    if source not in visited:
                        visited.add(source)
                        next_frontier.append(source)
                        related.append({
                            "entity": current_entity,
                            "relationship": data.get("relationship", "related_to"),
                            "connected_entity": source
                        })

            current_frontier = next_frontier

        return related

    def save(self):
        """
        Persist graph to JSON file.

        Uses NetworkX's node_link_data format for serialization.
        """
        graph_path = self._get_graph_path()

        try:
            data = nx.node_link_data(self.graph)
            with open(graph_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(
                f"Saved graph for user {self.user_id}: "
                f"{self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges"
            )
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")
            raise
