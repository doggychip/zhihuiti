"""Langfuse Bridge — LLM call tracing and cost tracking.

Wraps the langfuse SDK to trace every LLM call with token usage, cost,
and latency metadata. Also traces agent-level task completions.

Install: pip install langfuse
If langfuse is not installed, all methods are no-ops.

Configuration (via env or constructor args):
  LANGFUSE_PUBLIC_KEY — project public key
  LANGFUSE_SECRET_KEY — project secret key
  LANGFUSE_HOST       — self-hosted URL (default: https://cloud.langfuse.com)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


class LangfuseBridge:
    """Bridge to Langfuse for LLM observability and cost tracking.

    Lazy-initializes the Langfuse client on first use. If langfuse is not
    installed or credentials are missing, all tracing calls silently no-op.
    """

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
    ):
        self._public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        self._secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY", "")
        self._host = host or os.environ.get(
            "LANGFUSE_HOST", "https://cloud.langfuse.com"
        )
        self._client: Any = None
        self._available: bool | None = None
        self._call_count: int = 0
        self._total_tokens: int = 0
        self._total_cost: float = 0.0
        self._total_latency_ms: float = 0.0

    def is_available(self) -> bool:
        """Check if langfuse is installed and credentials are configured."""
        if self._available is not None:
            return self._available

        try:
            import langfuse  # noqa: F401
        except ImportError:
            logger.debug("langfuse not installed — LangfuseBridge disabled")
            self._available = False
            return False

        if not self._public_key or not self._secret_key:
            logger.debug(
                "LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set — "
                "LangfuseBridge disabled"
            )
            self._available = False
            return False

        self._available = True
        return True

    def _get_client(self) -> Any:
        """Lazy-init the Langfuse client."""
        if self._client is not None:
            return self._client

        if not self.is_available():
            return None

        try:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=self._public_key,
                secret_key=self._secret_key,
                host=self._host,
            )
            return self._client
        except Exception as e:
            logger.error("Failed to initialize Langfuse client: %s", e)
            self._available = False
            return None

    def trace_llm_call(
        self,
        model: str,
        system: str,
        user: str,
        response: str,
        usage: dict,
        duration_ms: float,
    ) -> None:
        """Log a completed LLM call with all metadata.

        Args:
            model: Model identifier (e.g. "claude-sonnet-4-20250514").
            system: System prompt text.
            user: User message text.
            response: Assistant response text.
            usage: Dict with input_tokens, output_tokens, and optional cache_read_input_tokens.
            duration_ms: Wall-clock latency in milliseconds.
        """
        # Always track local stats even if langfuse is unavailable
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = input_tokens + output_tokens
        self._call_count += 1
        self._total_tokens += total_tokens
        self._total_latency_ms += duration_ms

        client = self._get_client()
        if client is None:
            return

        try:
            trace = client.trace(name="llm-call", metadata={"model": model})
            trace.generation(
                name="completion",
                model=model,
                input=[
                    {"role": "system", "content": system[:500]},
                    {"role": "user", "content": user},
                ],
                output=response,
                usage={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                    "unit": "TOKENS",
                },
                metadata={
                    "duration_ms": duration_ms,
                    "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
                },
            )
        except Exception as e:
            logger.error("trace_llm_call failed: %s", e)

    def trace_agent_task(
        self,
        agent_id: str,
        role: str,
        task: str,
        score: float,
        tokens_used: int,
    ) -> None:
        """Log a completed agent task execution.

        Args:
            agent_id: Unique agent identifier.
            role: Agent role (coder, researcher, etc.).
            task: Task description.
            score: Quality score (0.0-1.0).
            tokens_used: Total tokens consumed by this task.
        """
        client = self._get_client()
        if client is None:
            return

        try:
            trace = client.trace(
                name="agent-task",
                user_id=agent_id,
                metadata={"role": role, "score": score},
            )
            trace.span(
                name="task-execution",
                input=task,
                output=f"score={score:.2f}",
                metadata={
                    "agent_id": agent_id,
                    "role": role,
                    "tokens_used": tokens_used,
                    "score": score,
                },
            )
        except Exception as e:
            logger.error("trace_agent_task failed: %s", e)

    def get_cost_summary(self) -> dict:
        """Return local cost tracking summary.

        Returns dict with total_cost, total_tokens, call_count, avg_latency_ms.
        Works even when langfuse is not installed (tracks locally).
        """
        avg_latency = (
            self._total_latency_ms / self._call_count
            if self._call_count > 0
            else 0.0
        )
        return {
            "total_cost": self._total_cost,
            "total_tokens": self._total_tokens,
            "call_count": self._call_count,
            "avg_latency_ms": round(avg_latency, 1),
        }

    def flush(self) -> None:
        """Flush any pending traces to the Langfuse server.

        Safe to call even if langfuse is not available.
        """
        if self._client is None:
            return

        try:
            self._client.flush()
        except Exception as e:
            logger.error("Langfuse flush failed: %s", e)


# Singleton for lazy initialization
_bridge: LangfuseBridge | None = None


def get_bridge(
    public_key: str | None = None,
    secret_key: str | None = None,
    host: str | None = None,
) -> LangfuseBridge:
    """Get or create the global Langfuse bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = LangfuseBridge(
            public_key=public_key, secret_key=secret_key, host=host
        )
    return _bridge
