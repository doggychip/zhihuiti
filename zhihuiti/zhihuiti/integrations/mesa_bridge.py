"""Mesa Bridge — agent-based modeling framework.

Wraps Mesa for formal economic simulations and parameter sweeps.
Enables testing token economy dynamics (tax rates, reward curves,
agent survival) in a controlled simulation before applying to live agents.

Integration points:
  - Economy modeling: simulate token flow, taxation, and agent survival
  - Parameter sweeps: batch-run across tax rates, initial tokens, etc.
  - Validation: verify economy parameters produce stable wealth distributions
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MesaBridge:
    """Bridge to Mesa for agent-based economic modeling."""

    def __init__(self):
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if mesa is installed."""
        if self._available is not None:
            return self._available
        try:
            import mesa  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False

    def create_economy_model(
        self,
        num_agents: int,
        initial_tokens: float = 100.0,
        tax_rate: float = 0.10,
    ) -> Any:
        """Create a Mesa economy model simulating zhihuiti token dynamics.

        Agents earn tokens by completing tasks (random quality), pay taxes,
        and are culled if their balance reaches zero.

        Args:
            num_agents: Number of agents in the simulation.
            initial_tokens: Starting token balance per agent.
            tax_rate: Tax rate applied to each reward (0.0 to 1.0).

        Returns:
            A Mesa Model instance, or None if unavailable.
        """
        if not self.is_available():
            return None
        try:
            import mesa  # type: ignore

            class EconAgent(mesa.Agent):
                """Agent that earns, pays tax, and may be culled."""

                def __init__(self, model: mesa.Model, tokens: float, tax: float):
                    super().__init__(model)
                    self.tokens = tokens
                    self.tax_rate = tax
                    self.alive = True
                    self.tasks_done = 0

                def step(self) -> None:
                    if not self.alive:
                        return
                    # Simulate task with random quality
                    quality = self.random.random()
                    reward = quality * 20.0
                    tax_amount = reward * self.tax_rate
                    net = reward - tax_amount
                    self.tokens += net
                    self.tasks_done += 1
                    # Operating cost per step
                    self.tokens -= 5.0
                    if self.tokens <= 0:
                        self.alive = False
                        self.tokens = 0.0

            class EconomyModel(mesa.Model):
                """Token economy simulation model."""

                def __init__(self, n: int, tokens: float, tax: float):
                    super().__init__()
                    self.num_agents = n
                    self.initial_tokens = tokens
                    self.tax_rate = tax
                    for _ in range(n):
                        EconAgent(self, tokens, tax)

                def step(self) -> None:
                    self.agents.shuffle_do("step")

            return EconomyModel(num_agents, initial_tokens, tax_rate)
        except Exception as e:
            logger.warning("mesa model creation failed: %s", e)
            return None

    def run_simulation(self, model: Any, steps: int = 100) -> dict[str, Any]:
        """Run the simulation for a given number of steps.

        Args:
            model: A Mesa Model instance (from create_economy_model).
            steps: Number of simulation steps to execute.

        Returns:
            Dict with gini, wealth_distribution, agent_survival_rate.
        """
        if model is None:
            return {"error": "model is None"}
        try:
            for _ in range(steps):
                model.step()

            agents = [a for a in model.agents if hasattr(a, "tokens")]
            alive = [a for a in agents if getattr(a, "alive", False)]
            wealths = sorted([a.tokens for a in agents], reverse=True)

            survival_rate = len(alive) / len(agents) if agents else 0.0
            gini = self._compute_gini(wealths)

            return {
                "gini": round(gini, 4),
                "wealth_distribution": [round(w, 2) for w in wealths[:20]],
                "agent_survival_rate": round(survival_rate, 4),
                "alive_count": len(alive),
                "total_agents": len(agents),
                "steps_run": steps,
            }
        except Exception as e:
            logger.warning("mesa simulation failed: %s", e)
            return {"error": str(e)}

    def batch_run(
        self,
        param_ranges: dict[str, list[Any]],
        iterations: int = 10,
        steps_per_run: int = 100,
        fixed_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run parameter sweep across multiple configurations.

        Args:
            param_ranges: Dict mapping param names to lists of values to sweep.
                         Supported keys: num_agents, initial_tokens, tax_rate.
            iterations: Number of repetitions per parameter combination.
            steps_per_run: Steps to simulate per run.
            fixed_params: Default values for params not being swept.

        Returns:
            List of result dicts, each including the params and outcome metrics.
        """
        if not self.is_available():
            return [{"error": "mesa not installed"}]

        defaults = {"num_agents": 20, "initial_tokens": 100.0, "tax_rate": 0.10}
        if fixed_params:
            defaults.update(fixed_params)

        # Generate parameter combinations
        keys = list(param_ranges.keys())
        combos: list[dict[str, Any]] = [{}]
        for key in keys:
            new_combos: list[dict[str, Any]] = []
            for combo in combos:
                for val in param_ranges[key]:
                    c = dict(combo)
                    c[key] = val
                    new_combos.append(c)
            combos = new_combos

        results: list[dict[str, Any]] = []
        for combo in combos:
            merged = dict(defaults)
            merged.update(combo)
            for _ in range(iterations):
                model = self.create_economy_model(
                    num_agents=int(merged["num_agents"]),
                    initial_tokens=float(merged["initial_tokens"]),
                    tax_rate=float(merged["tax_rate"]),
                )
                outcome = self.run_simulation(model, steps=steps_per_run)
                outcome["params"] = dict(merged)
                results.append(outcome)

        return results

    @staticmethod
    def _compute_gini(wealths: list[float]) -> float:
        """Compute Gini coefficient from a list of wealth values."""
        n = len(wealths)
        if n == 0:
            return 0.0
        total = sum(wealths)
        if total == 0:
            return 0.0
        sorted_w = sorted(wealths)
        cumulative = 0.0
        weighted_sum = 0.0
        for i, w in enumerate(sorted_w):
            cumulative += w
            weighted_sum += cumulative
        return (2 * weighted_sum) / (n * total) - (n + 1) / n


# Singleton for lazy initialization
_bridge: MesaBridge | None = None


def get_bridge() -> MesaBridge:
    """Get or create the global Mesa bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = MesaBridge()
    return _bridge
