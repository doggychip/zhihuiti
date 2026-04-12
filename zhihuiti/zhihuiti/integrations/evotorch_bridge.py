"""EvoTorch Bridge — GPU-accelerated evolutionary optimization.

Wraps EvoTorch for mathematically rigorous agent evolution.
Provides CMA-ES and other evolutionary strategies accelerated by PyTorch
for optimizing agent parameters, trait vectors, and strategy weights.

Integration points:
  - Parameter optimization: find optimal agent hyperparameters via CMA-ES
  - Trait evolution: evolve populations of trait vectors with fitness scoring
  - Economy tuning: optimize tax rates, reward curves, bidding strategies
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EvoTorchBridge:
    """Bridge to EvoTorch for GPU-accelerated evolutionary optimization."""

    def __init__(self, device: str = "cpu"):
        self._device = device
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if evotorch is installed."""
        if self._available is not None:
            return self._available
        try:
            import evotorch  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False

    def optimize_parameters(
        self,
        fitness_fn: Callable[[Any], float],
        param_bounds: dict[str, tuple[float, float]],
        population_size: int = 50,
        generations: int = 100,
    ) -> dict[str, Any]:
        """Run CMA-ES optimization over a parameter space.

        Args:
            fitness_fn: Callable that takes a parameter tensor and returns a scalar fitness.
            param_bounds: Dict mapping param names to (min, max) tuples.
            population_size: Number of candidate solutions per generation.
            generations: Number of evolutionary generations to run.

        Returns:
            Dict with keys: best_params, best_fitness, history (per-generation best).
        """
        if not self.is_available():
            return {"error": "evotorch not installed"}
        try:
            import torch
            from evotorch import Problem  # type: ignore
            from evotorch.algorithms import CMAES  # type: ignore

            param_names = list(param_bounds.keys())
            bounds_lower = [param_bounds[k][0] for k in param_names]
            bounds_upper = [param_bounds[k][1] for k in param_names]
            n_dims = len(param_names)

            def _wrapped_fitness(x: torch.Tensor) -> torch.Tensor:
                scores = []
                for row in x:
                    scores.append(fitness_fn(row))
                return torch.tensor(scores, dtype=x.dtype, device=x.device)

            problem = Problem(
                "max",
                _wrapped_fitness,
                solution_length=n_dims,
                initial_bounds=(bounds_lower, bounds_upper),
                device=self._device,
            )

            searcher = CMAES(problem, popsize=population_size, stdev_init=0.5)

            history: list[float] = []
            for _ in range(generations):
                searcher.step()
                best_fitness = float(searcher.status.get("best_eval", 0.0))
                history.append(best_fitness)

            best_solution = searcher.status.get("best", None)
            best_params = {}
            if best_solution is not None:
                values = best_solution.values.detach().cpu().tolist()
                best_params = dict(zip(param_names, values))

            return {
                "best_params": best_params,
                "best_fitness": history[-1] if history else 0.0,
                "history": history,
            }
        except Exception as e:
            logger.warning("evotorch optimize failed: %s", e)
            return {"error": str(e)}

    def evolve_traits(
        self,
        current_traits: list[dict[str, float]],
        fitness_scores: list[float],
        mutation_rate: float = 0.1,
    ) -> list[dict[str, float]]:
        """Evolve a population of trait vectors using fitness-proportional selection.

        Args:
            current_traits: List of trait dicts (one per agent in the population).
            fitness_scores: Fitness score for each agent (higher is better).
            mutation_rate: Standard deviation of Gaussian mutation noise.

        Returns:
            New population of trait dicts (same size as input).
        """
        if not current_traits or not fitness_scores:
            return current_traits
        if not self.is_available():
            return current_traits
        try:
            import torch

            # Convert trait dicts to tensor
            keys = list(current_traits[0].keys())
            pop_matrix = torch.tensor(
                [[t.get(k, 0.0) for k in keys] for t in current_traits],
                dtype=torch.float32,
                device=self._device,
            )
            scores = torch.tensor(fitness_scores, dtype=torch.float32, device=self._device)

            # Fitness-proportional selection probabilities
            shifted = scores - scores.min()
            probs = shifted / (shifted.sum() + 1e-8)

            # Sample parents and create offspring with mutation
            n = len(current_traits)
            parent_indices = torch.multinomial(probs, n, replacement=True)
            offspring = pop_matrix[parent_indices].clone()
            noise = torch.randn_like(offspring) * mutation_rate
            offspring = offspring + noise

            # Convert back to trait dicts
            result: list[dict[str, float]] = []
            for row in offspring:
                trait = {k: round(float(v), 6) for k, v in zip(keys, row)}
                result.append(trait)
            return result
        except Exception as e:
            logger.warning("evotorch evolve_traits failed: %s", e)
            return current_traits


# Singleton for lazy initialization
_bridge: EvoTorchBridge | None = None


def get_bridge(device: str = "cpu") -> EvoTorchBridge:
    """Get or create the global EvoTorch bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = EvoTorchBridge(device=device)
    return _bridge
