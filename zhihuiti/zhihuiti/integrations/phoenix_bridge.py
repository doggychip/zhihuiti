"""Phoenix Bridge — embedding drift detection and experiment tracking.

Wraps Arize Phoenix (https://github.com/Arize-ai/phoenix) for statistical
behavior monitoring of agent outputs. Detects when agent embeddings drift
from baseline, indicating degraded or changed behavior.

Integration points:
  - After task execution: log embeddings and evaluation scores
  - Periodic: compare recent embeddings against baseline for drift
  - Dashboard: start Phoenix session for interactive exploration
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PhoenixBridge:
    """Bridge to Arize Phoenix for AI observability and drift detection."""

    def __init__(self, project_name: str = "zhihuiti"):
        self._project_name = project_name
        self._available: bool | None = None
        self._session: Any = None

    def is_available(self) -> bool:
        """Check if Phoenix is installed and accessible."""
        if self._available is not None:
            return self._available
        try:
            import phoenix  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False

    def start_session(self) -> None:
        """Launch a Phoenix session for interactive exploration.

        Starts the Phoenix UI server (typically at http://localhost:6006).
        No-op if Phoenix is unavailable or session already active.
        """
        if not self.is_available() or self._session is not None:
            return
        try:
            import phoenix as px
            self._session = px.launch_app()
            logger.info("Phoenix session started: %s", self._session.url if hasattr(self._session, 'url') else 'running')
        except Exception as e:
            logger.warning("Phoenix session start failed: %s", e)

    def log_embedding(
        self,
        text: str,
        embedding: list[float] | None = None,
        label: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Log a text embedding for drift monitoring.

        Args:
            text: The raw text that was embedded.
            embedding: Pre-computed embedding vector. If None, Phoenix
                       will attempt to compute one.
            label: Optional classification label (e.g., agent role).
            metadata: Optional metadata dict (agent_id, task_id, etc.).
        """
        if not self.is_available():
            return
        try:
            import phoenix as px
            record: dict[str, Any] = {"text": text}
            if embedding is not None:
                record["embedding"] = embedding
            if label is not None:
                record["label"] = label
            if metadata:
                record.update(metadata)
            # Use Phoenix inferences API if available
            if hasattr(px, "Client"):
                client = px.Client()
                client.log_traces([record])
            else:
                logger.debug("Phoenix log_embedding: client API not available, skipping")
        except Exception as e:
            logger.warning("Phoenix log_embedding failed: %s", e)

    def log_evaluation(
        self,
        input_text: str,
        output_text: str,
        score: float,
        agent_id: str | None = None,
    ) -> None:
        """Log an evaluation result for tracking agent performance over time.

        Args:
            input_text: The task/prompt given to the agent.
            output_text: The agent's response/output.
            score: Numeric quality score (0.0-1.0).
            agent_id: Optional agent identifier.
        """
        if not self.is_available():
            return
        try:
            import phoenix as px
            record: dict[str, Any] = {
                "input": input_text,
                "output": output_text,
                "score": score,
                "project": self._project_name,
            }
            if agent_id:
                record["agent_id"] = agent_id
            if hasattr(px, "Client"):
                client = px.Client()
                client.log_evaluations([record])
            else:
                logger.debug("Phoenix log_evaluation: client API not available, skipping")
        except Exception as e:
            logger.warning("Phoenix log_evaluation failed: %s", e)

    def detect_drift(
        self,
        recent_embeddings: list[list[float]],
        baseline_embeddings: list[list[float]],
    ) -> dict:
        """Compare recent embeddings against a baseline to detect drift.

        Uses statistical distance measures (e.g., PSI, cosine distance)
        to determine whether agent behavior has shifted significantly.

        Args:
            recent_embeddings: Embedding vectors from recent agent outputs.
            baseline_embeddings: Embedding vectors from the known-good baseline.

        Returns:
            Dict with keys: 'drifted' (bool), 'distance' (float),
            'threshold' (float), 'method' (str).
        """
        default = {"drifted": False, "distance": 0.0, "threshold": 0.1, "method": "none"}
        if not self.is_available():
            return default
        if not recent_embeddings or not baseline_embeddings:
            return default
        try:
            # Compute mean cosine distance between centroids
            dim = len(recent_embeddings[0])
            recent_centroid = [sum(e[i] for e in recent_embeddings) / len(recent_embeddings) for i in range(dim)]
            baseline_centroid = [sum(e[i] for e in baseline_embeddings) / len(baseline_embeddings) for i in range(dim)]

            dot = sum(a * b for a, b in zip(recent_centroid, baseline_centroid))
            norm_r = sum(a * a for a in recent_centroid) ** 0.5
            norm_b = sum(b * b for b in baseline_centroid) ** 0.5
            cosine_sim = dot / (norm_r * norm_b) if (norm_r * norm_b) > 0 else 0.0
            distance = 1.0 - cosine_sim
            threshold = 0.1

            return {
                "drifted": distance > threshold,
                "distance": round(distance, 6),
                "threshold": threshold,
                "method": "cosine_centroid",
            }
        except Exception as e:
            logger.warning("Phoenix detect_drift failed: %s", e)
            return default


# Singleton for lazy initialization
_bridge: PhoenixBridge | None = None


def get_bridge(project_name: str = "zhihuiti") -> PhoenixBridge:
    """Get or create the global Phoenix bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = PhoenixBridge(project_name=project_name)
    return _bridge
