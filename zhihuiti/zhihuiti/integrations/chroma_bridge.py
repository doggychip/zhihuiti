"""Chroma Bridge — vector database for semantic agent memory.

Wraps chromadb for embedding-based search over agent knowledge.
Stores task results, agent outputs, and arbitrary text with metadata,
enabling semantic retrieval for context injection.

Install: pip install chromadb
If chromadb is not installed, all methods gracefully return empty results.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "zhihuiti"


class ChromaBridge:
    """Bridge to ChromaDB for vector semantic search.

    Lazy-initializes the ChromaDB client and collection on first use.
    If chromadb is not installed, is_available() returns False and all
    methods return empty results.
    """

    def __init__(self, persist_dir: str | None = None):
        self._persist_dir = persist_dir
        self._client: Any = None
        self._collection: Any = None
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if chromadb is installed."""
        if self._available is not None:
            return self._available

        try:
            import chromadb  # noqa: F401
            self._available = True
        except ImportError:
            logger.debug("chromadb not installed — ChromaBridge disabled")
            self._available = False

        return self._available

    def _get_collection(self) -> Any:
        """Lazy-init the ChromaDB client and collection."""
        if self._collection is not None:
            return self._collection

        if not self.is_available():
            return None

        try:
            import chromadb

            if self._persist_dir:
                self._client = chromadb.PersistentClient(path=self._persist_dir)
            else:
                self._client = chromadb.Client()

            self._collection = self._client.get_or_create_collection(
                name=DEFAULT_COLLECTION,
                metadata={"description": "zhihuiti agent memory"},
            )
            return self._collection
        except Exception as e:
            logger.error("Failed to initialize ChromaDB: %s", e)
            self._available = False
            return None

    def add(
        self,
        text: str,
        metadata: dict | None = None,
        doc_id: str | None = None,
    ) -> None:
        """Add text with optional metadata to the vector store.

        Args:
            text: Content to embed and store.
            metadata: Optional dict (agent_role, score, goal_id, etc.).
                      Values must be str, int, float, or bool for chromadb.
            doc_id: Optional document ID. Auto-generated from text hash if omitted.
        """
        collection = self._get_collection()
        if collection is None:
            return

        if doc_id is None:
            doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]

        # Sanitize metadata: chromadb only accepts str, int, float, bool values
        clean_meta = {}
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)

        try:
            collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[clean_meta] if clean_meta else None,
            )
        except Exception as e:
            logger.error("ChromaBridge add failed: %s", e)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Semantic search over stored documents.

        Args:
            query: Natural language search query.
            limit: Maximum number of results.

        Returns list of dicts with keys: text, metadata, distance.
        Returns empty list if chromadb is unavailable or search fails.
        """
        collection = self._get_collection()
        if collection is None:
            return []

        try:
            results = collection.query(
                query_texts=[query],
                n_results=min(limit, self.count() or limit),
            )

            items = []
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for i, doc in enumerate(documents):
                items.append({
                    "text": doc,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distances[i] if i < len(distances) else None,
                })

            return items
        except Exception as e:
            logger.error("ChromaBridge search failed: %s", e)
            return []

    def add_task_result(
        self,
        task_desc: str,
        result: str,
        agent_role: str,
        score: float,
        goal_id: str = "",
    ) -> None:
        """Convenience method: format and add a completed task result.

        Combines task description and result into a single document with
        structured metadata for later filtering and retrieval.
        """
        text = (
            f"Task: {task_desc}\n"
            f"Agent: {agent_role}\n"
            f"Score: {score:.2f}\n"
            f"Result: {result[:2000]}"
        )
        metadata = {
            "agent_role": agent_role,
            "score": score,
            "type": "task_result",
        }
        if goal_id:
            metadata["goal_id"] = goal_id

        # Deterministic ID from task + role so re-runs update rather than duplicate
        doc_id = hashlib.sha256(
            f"{task_desc}:{agent_role}".encode()
        ).hexdigest()[:16]

        self.add(text=text, metadata=metadata, doc_id=doc_id)

    def count(self) -> int:
        """Return the number of documents in the collection.

        Returns 0 if chromadb is unavailable.
        """
        collection = self._get_collection()
        if collection is None:
            return 0

        try:
            return collection.count()
        except Exception as e:
            logger.error("ChromaBridge count failed: %s", e)
            return 0


# Singleton for lazy initialization
_bridge: ChromaBridge | None = None


def get_bridge(persist_dir: str | None = None) -> ChromaBridge:
    """Get or create the global ChromaDB bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = ChromaBridge(persist_dir=persist_dir)
    return _bridge
