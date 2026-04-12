"""Integrations — optional third-party bridges for zhihuiti agents.

All bridges follow the lazy-init pattern: try import on first use,
return empty/graceful results if the dependency is not installed.
No required dependencies — each bridge is fully optional.

Available bridges:
  - ccxt_bridge: Unified exchange API (100+ exchanges) for live trading
  - langfuse_bridge: LLM call tracing and cost tracking
  - chroma_bridge: Vector semantic search over agent memory
"""

from zhihuiti.integrations.ccxt_bridge import get_bridge as get_ccxt_bridge
from zhihuiti.integrations.langfuse_bridge import get_bridge as get_langfuse_bridge
from zhihuiti.integrations.chroma_bridge import get_bridge as get_chroma_bridge

__all__ = [
    "get_ccxt_bridge",
    "get_langfuse_bridge",
    "get_chroma_bridge",
]
