"""GraphRAG Bridge — knowledge graph construction and graph-based retrieval.

Wraps Microsoft GraphRAG for structured knowledge synthesis.
Builds a knowledge graph from documents and supports both global
(community-summary) and local (entity-focused) query modes.

Integration points:
  - Index: build knowledge graph from task results and documents
  - Global query: high-level synthesis across all knowledge
  - Local query: entity-focused retrieval for specific questions
  - Inspection: extract entities and communities for economy auditing
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = os.path.expanduser("~/.zhihuiti/graphrag")


class GraphRAGBridge:
    """Bridge to Microsoft GraphRAG for knowledge graph RAG."""

    def __init__(self, storage_dir: str | None = None):
        self._storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self._available: bool | None = None
        self._settings: Any = None

    def is_available(self) -> bool:
        """Check if graphrag is installed."""
        if self._available is not None:
            return self._available
        try:
            import graphrag  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False

    def _ensure_storage(self) -> None:
        """Create storage directory if it does not exist."""
        os.makedirs(self._storage_dir, exist_ok=True)

    def _get_settings(self) -> Any:
        """Lazily load GraphRAG settings."""
        if self._settings is not None:
            return self._settings
        if not self.is_available():
            return None
        try:
            from graphrag.config import create_graphrag_config  # type: ignore

            self._ensure_storage()
            self._settings = create_graphrag_config(root_dir=self._storage_dir)
            return self._settings
        except Exception as e:
            logger.warning("graphrag settings load failed: %s", e)
            return None

    def index_documents(
        self,
        texts: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build or update knowledge graph from texts.

        Args:
            texts: List of document texts to index.
            metadata: Optional per-document metadata dicts.

        Returns:
            Dict with keys: entities_count, relationships_count, communities_count.
        """
        if not self.is_available():
            return {"error": "graphrag not installed"}
        try:
            from graphrag.index import run_pipeline_with_config  # type: ignore

            self._ensure_storage()
            settings = self._get_settings()
            if settings is None:
                return {"error": "failed to load graphrag settings"}

            # Write texts to input directory for indexing
            input_dir = os.path.join(self._storage_dir, "input")
            os.makedirs(input_dir, exist_ok=True)
            for i, text in enumerate(texts):
                filepath = os.path.join(input_dir, f"doc_{i:04d}.txt")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(text)

            result = run_pipeline_with_config(settings)
            stats = result if isinstance(result, dict) else {}
            return {
                "entities_count": stats.get("entities_count", len(texts)),
                "relationships_count": stats.get("relationships_count", 0),
                "communities_count": stats.get("communities_count", 0),
            }
        except Exception as e:
            logger.warning("graphrag indexing failed: %s", e)
            return {"error": str(e)}

    def query_global(self, question: str) -> str:
        """Global search using community summaries.

        Args:
            question: Natural language question for high-level synthesis.

        Returns:
            Synthesized answer string.
        """
        if not self.is_available():
            return ""
        try:
            from graphrag.query import global_search  # type: ignore

            settings = self._get_settings()
            if settings is None:
                return ""
            result = global_search(settings, question)
            return str(result) if result else ""
        except Exception as e:
            logger.warning("graphrag global query failed: %s", e)
            return ""

    def query_local(self, question: str) -> str:
        """Local search using entity-focused retrieval.

        Args:
            question: Natural language question for entity-focused lookup.

        Returns:
            Answer string grounded in specific entities.
        """
        if not self.is_available():
            return ""
        try:
            from graphrag.query import local_search  # type: ignore

            settings = self._get_settings()
            if settings is None:
                return ""
            result = local_search(settings, question)
            return str(result) if result else ""
        except Exception as e:
            logger.warning("graphrag local query failed: %s", e)
            return ""

    def get_entities(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve extracted entities from the knowledge graph.

        Args:
            limit: Maximum number of entities to return.

        Returns:
            List of entity dicts with 'name', 'type', and 'description' keys.
        """
        if not self.is_available():
            return []
        try:
            from graphrag.query import get_entities as _get_entities  # type: ignore

            settings = self._get_settings()
            if settings is None:
                return []
            entities = _get_entities(settings, limit=limit)
            return entities if isinstance(entities, list) else []
        except Exception as e:
            logger.warning("graphrag get_entities failed: %s", e)
            return []

    def get_communities(self) -> list[dict[str, Any]]:
        """Retrieve detected communities from the knowledge graph.

        Returns:
            List of community dicts with 'id', 'title', 'summary', 'members'.
        """
        if not self.is_available():
            return []
        try:
            from graphrag.query import get_communities as _get_communities  # type: ignore

            settings = self._get_settings()
            if settings is None:
                return []
            communities = _get_communities(settings)
            return communities if isinstance(communities, list) else []
        except Exception as e:
            logger.warning("graphrag get_communities failed: %s", e)
            return []


# Singleton for lazy initialization
_bridge: GraphRAGBridge | None = None


def get_bridge(storage_dir: str | None = None) -> GraphRAGBridge:
    """Get or create the global GraphRAG bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = GraphRAGBridge(storage_dir=storage_dir)
    return _bridge
