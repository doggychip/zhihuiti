"""PettingZoo Bridge — multi-agent reinforcement learning environments.

Wraps PettingZoo for training agent bidding and trading strategies.
Provides custom environments where agents learn competitive bidding,
resource allocation, and market-making through multi-agent RL.

Integration points:
  - Bidding training: agents learn optimal bid amounts through competition
  - Policy extraction: export learned policies for use in the economy layer
  - Strategy evaluation: test bidding strategies in simulated markets
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class PettingZooBridge:
    """Bridge to PettingZoo for multi-agent RL environments."""

    def __init__(self):
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if pettingzoo is installed."""
        if self._available is not None:
            return self._available
        try:
            import pettingzoo  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False

    def create_bidding_env(
        self,
        num_agents: int,
        task_pool_size: int,
        max_budget: float = 100.0,
    ) -> Any:
        """Create a custom multi-agent bidding environment.

        Agents observe a task description embedding and their own budget,
        then submit bids. Lowest qualified bid wins and earns a reward
        proportional to task quality score minus bid cost.

        Args:
            num_agents: Number of competing agents.
            task_pool_size: Number of tasks available per episode.
            max_budget: Starting budget for each agent.

        Returns:
            A PettingZoo AEC environment instance, or None if unavailable.
        """
        if not self.is_available():
            return None
        try:
            from pettingzoo.utils import agent_selector  # type: ignore
            import numpy as np  # type: ignore
            from gymnasium import spaces  # type: ignore

            class BiddingEnv:
                """Minimal AEC-style bidding environment."""

                metadata = {"name": "zhihuiti_bidding_v0"}

                def __init__(self, n_agents: int, n_tasks: int, budget: float):
                    self.possible_agents = [f"agent_{i}" for i in range(n_agents)]
                    self.n_tasks = n_tasks
                    self.max_budget = budget
                    self.observation_spaces = {
                        a: spaces.Box(low=0, high=1, shape=(n_tasks + 1,), dtype=np.float32)
                        for a in self.possible_agents
                    }
                    self.action_spaces = {
                        a: spaces.Box(low=0, high=float(budget), shape=(1,), dtype=np.float32)
                        for a in self.possible_agents
                    }
                    self.reset()

                def reset(self) -> None:
                    self.agents = list(self.possible_agents)
                    self.budgets = {a: self.max_budget for a in self.agents}
                    self.task_values = np.random.uniform(0.1, 1.0, self.n_tasks).astype(np.float32)
                    self.current_task = 0
                    self.bids: dict[str, float] = {}
                    self.rewards = {a: 0.0 for a in self.agents}
                    self._selector = agent_selector(self.agents)
                    self.agent_selection = self._selector.reset()

                def observe(self, agent: str) -> Any:
                    budget_norm = self.budgets.get(agent, 0.0) / self.max_budget
                    obs = np.append(self.task_values, budget_norm).astype(np.float32)
                    return obs

                def step(self, action: Any) -> None:
                    agent = self.agent_selection
                    bid = float(np.clip(action, 0, self.budgets.get(agent, 0)))
                    self.bids[agent] = bid

                    if len(self.bids) == len(self.agents):
                        winner = min(self.bids, key=lambda a: self.bids[a])
                        task_val = self.task_values[self.current_task % self.n_tasks]
                        self.rewards[winner] += float(task_val) - self.bids[winner]
                        self.budgets[winner] -= self.bids[winner]
                        self.bids = {}
                        self.current_task += 1

                    self.agent_selection = self._selector.next()

            return BiddingEnv(num_agents, task_pool_size, max_budget)
        except Exception as e:
            logger.warning("pettingzoo env creation failed: %s", e)
            return None

    def train_episode(
        self,
        env: Any,
        agents: dict[str, Callable] | None = None,
        steps: int = 1000,
    ) -> dict[str, Any]:
        """Run one training episode through the environment.

        Args:
            env: A PettingZoo-compatible environment instance.
            agents: Optional dict mapping agent names to policy callables.
                    Each callable takes an observation and returns an action.
                    If None, uses random policies.
            steps: Maximum steps per episode.

        Returns:
            Dict with keys: rewards (per-agent), total_steps, tasks_completed.
        """
        if env is None:
            return {"error": "environment is None"}
        try:
            import numpy as np

            env.reset()
            total_steps = 0

            for _ in range(steps):
                if not env.agents:
                    break
                agent_name = env.agent_selection
                obs = env.observe(agent_name)

                if agents and agent_name in agents:
                    action = agents[agent_name](obs)
                else:
                    # Random policy fallback
                    space = env.action_spaces[agent_name]
                    action = space.sample()

                env.step(action)
                total_steps += 1

            return {
                "rewards": dict(env.rewards),
                "total_steps": total_steps,
                "tasks_completed": getattr(env, "current_task", 0),
            }
        except Exception as e:
            logger.warning("pettingzoo train_episode failed: %s", e)
            return {"error": str(e)}

    def get_learned_policy(self, agent_id: str) -> dict[str, Any]:
        """Extract learned policy parameters for a trained agent.

        In practice this would load from a trained model checkpoint.
        Returns a serializable dict of policy weights/parameters.

        Args:
            agent_id: Identifier of the agent whose policy to extract.

        Returns:
            Dict with policy parameters, or empty dict if not available.
        """
        # Placeholder: in a full implementation this would load a saved
        # policy network and extract its parameters as numpy arrays / lists.
        logger.info("get_learned_policy called for %s (not yet trained)", agent_id)
        return {"agent_id": agent_id, "policy_type": "random", "weights": {}}


# Singleton for lazy initialization
_bridge: PettingZooBridge | None = None


def get_bridge() -> PettingZooBridge:
    """Get or create the global PettingZoo bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = PettingZooBridge()
    return _bridge
