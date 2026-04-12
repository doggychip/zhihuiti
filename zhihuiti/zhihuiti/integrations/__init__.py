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
  - freqtrade_bridge: Backtesting engine and risk management
  - graphrag_bridge: Knowledge graph construction and graph-based RAG
  - evotorch_bridge: GPU-accelerated evolutionary optimization
  - pettingzoo_bridge: Multi-agent reinforcement learning environments
  - mesa_bridge: Agent-based modeling and economic simulations
"""

from zhihuiti.integrations.nautilus_bridge import get_bridge as get_nautilus_bridge
from zhihuiti.integrations.temporal_bridge import get_bridge as get_temporal_bridge
from zhihuiti.integrations.swebench_bridge import get_bridge as get_swebench_bridge
from zhihuiti.integrations.freqtrade_bridge import get_bridge as get_freqtrade_bridge
from zhihuiti.integrations.graphrag_bridge import get_bridge as get_graphrag_bridge
from zhihuiti.integrations.evotorch_bridge import get_bridge as get_evotorch_bridge
from zhihuiti.integrations.pettingzoo_bridge import get_bridge as get_pettingzoo_bridge
from zhihuiti.integrations.mesa_bridge import get_bridge as get_mesa_bridge

__all__ = [
    "get_nautilus_bridge",
    "get_temporal_bridge",
    "get_swebench_bridge",
    "get_freqtrade_bridge",
    "get_graphrag_bridge",
    "get_evotorch_bridge",
    "get_pettingzoo_bridge",
    "get_mesa_bridge",
]
