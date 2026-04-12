"""zhihuiti integrations — optional bridge modules for external tools.

Each bridge follows the same pattern:
  - Lazy init with try/except on import
  - is_available() check before any operation
  - Graceful degradation (returns empty/False on failure)
  - Module-level get_bridge() singleton
  - No required dependencies

Available bridges:
  - nautilus_bridge: Institutional-grade trading execution (NautilusTrader)
  - temporal_bridge: Durable workflow orchestration (Temporal)
  - swebench_bridge: Standardized coding agent evaluation (SWE-bench)
"""

from zhihuiti.integrations.nautilus_bridge import get_bridge as get_nautilus_bridge
from zhihuiti.integrations.temporal_bridge import get_bridge as get_temporal_bridge
from zhihuiti.integrations.swebench_bridge import get_bridge as get_swebench_bridge

__all__ = [
    "get_nautilus_bridge",
    "get_temporal_bridge",
    "get_swebench_bridge",
]
