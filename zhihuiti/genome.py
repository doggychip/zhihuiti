"""Strategy Genome — evolvable parameters that define agent behavior.

Each agent has a StrategyGenome that controls HOW it acts:
- Which actions are available (hard constraints)
- How aggressively it bids, trades, and breeds
- Whether it specializes or generalizes

The genome evolves through crossover (breeding) and mutation.
Traits are floats in [0, 1]. The LLM reasons within constraints
set by the genome — the genome defines what's POSSIBLE, the LLM
decides what to DO.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, fields


@dataclass
class StrategyGenome:
    """Six evolvable traits that constrain agent behavior."""

    bid_aggression: float = 0.5      # 0=conservative, 1=aggressive
    risk_tolerance: float = 0.5      # willingness to take hard tasks
    cooperation_bias: float = 0.5    # tendency to trade vs hoard
    specialization: float = 0.5      # deep specialist vs broad generalist
    price_sensitivity: float = 0.5   # how much market price affects decisions
    breeding_investment: float = 0.5  # willingness to pay for good genes

    def to_dict(self) -> dict[str, float]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> StrategyGenome:
        return cls(**{k: v for k, v in d.items() if k in {f.name for f in fields(cls)}})


def random_genome() -> StrategyGenome:
    """Create a genome with random traits in [0, 1]."""
    return StrategyGenome(
        bid_aggression=random.random(),
        risk_tolerance=random.random(),
        cooperation_bias=random.random(),
        specialization=random.random(),
        price_sensitivity=random.random(),
        breeding_investment=random.random(),
    )


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def crossover(
    parent_a: StrategyGenome,
    parent_b: StrategyGenome,
    bias: float = 0.6,
) -> StrategyGenome:
    """Weighted average crossover of two genomes.

    bias: weight toward parent_a (0.5 = equal, 1.0 = clone of a).
    All output traits are clamped to [0, 1].
    """
    result = {}
    for f in fields(StrategyGenome):
        val_a = getattr(parent_a, f.name)
        val_b = getattr(parent_b, f.name)
        result[f.name] = _clamp(val_a * bias + val_b * (1 - bias))
    return StrategyGenome(**result)


def mutate(
    genome: StrategyGenome,
    rate: float = 0.15,
) -> StrategyGenome:
    """Apply gaussian noise to genome traits.

    Each trait has `rate` probability of mutation.
    Mutation magnitude scales with rate: higher rate = bigger jumps.
    Output is always clamped to [0, 1].
    """
    result = {}
    for f in fields(StrategyGenome):
        val = getattr(genome, f.name)
        if random.random() < rate:
            # Scale noise by rate: rate=0.15 → sigma≈0.08, rate=0.35 → sigma≈0.18
            sigma = 0.05 + 0.4 * rate
            delta = random.gauss(0, sigma)
            val = _clamp(val + delta)
        result[f.name] = val
    return StrategyGenome(**result)


def classify_archetype(genome: StrategyGenome) -> str:
    """Classify a genome into one of four archetypes.

    - specialist: high specialization, conservative bidding
    - predator: aggressive bidding, low cooperation
    - trader: high cooperation, invests in breeding
    - generalist: everything else
    """
    if genome.specialization > 0.7 and genome.bid_aggression < 0.4:
        return "specialist"
    if genome.bid_aggression > 0.7 and genome.cooperation_bias < 0.3:
        return "predator"
    if genome.cooperation_bias > 0.7 and genome.breeding_investment > 0.5:
        return "trader"
    return "generalist"
