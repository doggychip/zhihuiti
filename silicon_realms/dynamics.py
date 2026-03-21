"""
Theoretical Dynamics
====================
Four theory-grounded enrichments for the Silicon Realms simulation:

1. Replicator Dynamics (EGT)       — strategy frequencies evolve by fitness
2. Statistical Mechanics           — temperature + entropy of token economy
3. Control Theory (Bellman)        — value function guides realm migration
4. Self-Organized Criticality      — detect phase transitions & avalanches
"""
from __future__ import annotations

import math
from .models import SimState


# ─────────────────────────────────────────────────────────────────────────────
# 1. REPLICATOR DYNAMICS
# Equation: dx_i/dt = x_i (f_i - φ̄)
# Strategies with above-mean fitness spread; below-mean strategies shrink.
# Implemented as a probabilistic imitation rule:
#   agents in below-average strategies occasionally copy a fitter agent's strategy.
# ─────────────────────────────────────────────────────────────────────────────

def evolve_strategies(state: SimState):
    """
    Apply replicator dynamics: strategies with above-mean fitness spread.

    Fitness = agent wealth (balance + staked).
    Each tick, agents in below-average strategies have a small probability
    of switching to a high-fitness strategy (imitation / selection).
    """
    if not state.agents:
        return

    # Compute per-strategy mean fitness
    strat_fitness: dict[str, list[float]] = {}
    for agent in state.agents.values():
        w = agent.balance + agent.staked
        strat_fitness.setdefault(agent.strategy, []).append(w)
        # Track individual fitness for history
        agent.fitness_history.append(w)
        if len(agent.fitness_history) > 20:
            agent.fitness_history.pop(0)

    strat_mean: dict[str, float] = {
        s: sum(ws) / len(ws) for s, ws in strat_fitness.items()
    }
    all_fitnesses = [w for ws in strat_fitness.values() for w in ws]
    mean_fitness = sum(all_fitnesses) / len(all_fitnesses)

    # Replicator dynamics imitation rule
    mutation_rate = state.config.get("dynamics", {}).get("mutation_rate", 0.03)
    for agent in state.agents.values():
        agent_fitness = agent.balance + agent.staked
        # Probability of strategy switch proportional to fitness deficit
        if agent_fitness < mean_fitness:
            deficit = (mean_fitness - agent_fitness) / (mean_fitness + 1e-9)
            p_switch = mutation_rate * deficit
            if state.rng.random() < p_switch:
                # Pick strategy proportional to its mean fitness (softmax selection)
                strategies = list(strat_mean.keys())
                weights = [max(0, strat_mean[s]) for s in strategies]
                total_w = sum(weights) + 1e-9
                r = state.rng.random() * total_w
                cumsum = 0.0
                for s, w in zip(strategies, weights):
                    cumsum += w
                    if r <= cumsum:
                        agent.strategy = s
                        break


def strategy_frequencies(state: SimState) -> dict[str, float]:
    """Return current frequency of each strategy (sums to 1)."""
    counts: dict[str, int] = {}
    for agent in state.agents.values():
        counts[agent.strategy] = counts.get(agent.strategy, 0) + 1
    total = len(state.agents) or 1
    return {s: c / total for s, c in counts.items()}


# ─────────────────────────────────────────────────────────────────────────────
# 2. STATISTICAL MECHANICS
# The token economy as a thermodynamic system:
#   - Temperature T = variance/mean of wealth (measures spread / disorder)
#   - Entropy H = -Σ p_i log p_i of normalised wealth distribution
#   - Low T: wealth concentrates (ordered phase)
#   - High T: wealth disperses (disordered phase)
# ─────────────────────────────────────────────────────────────────────────────

def compute_temperature(state: SimState) -> float:
    """
    Economic temperature = coefficient of variation of wealth.
    T ∝ std(wealth) / mean(wealth)
    Range: ~0 (perfect equality) to >>1 (extreme inequality).
    """
    wealths = [a.balance + a.staked for a in state.agents.values() if a.balance + a.staked > 0]
    if len(wealths) < 2:
        return 1.0
    mean_w = sum(wealths) / len(wealths)
    if mean_w < 1e-9:
        return 1.0
    variance = sum((w - mean_w) ** 2 for w in wealths) / len(wealths)
    return math.sqrt(variance) / mean_w


def compute_entropy(state: SimState) -> float:
    """
    Shannon entropy of the wealth distribution.
    H = -Σ p_i log p_i  where p_i = wealth_i / total_wealth
    Maximum when all agents have equal wealth; zero with one agent holding all.
    """
    wealths = [a.balance + a.staked for a in state.agents.values()]
    total = sum(wealths)
    if total < 1e-9:
        return 0.0
    entropy = 0.0
    for w in wealths:
        p = w / total
        if p > 1e-12:
            entropy -= p * math.log(p)
    return entropy


def update_thermodynamics(state: SimState):
    """Compute and store temperature and entropy in state."""
    state.temperature = compute_temperature(state)
    state.entropy = compute_entropy(state)


# ─────────────────────────────────────────────────────────────────────────────
# 3. CONTROL THEORY: BELLMAN VALUE FUNCTION
# V(realm) = expected discounted future reward for an agent in that realm.
# Computed via temporal-difference update (one-step Bellman backup):
#   V(realm) ← (1-α) V(realm) + α [r_observed + γ · V(realm)]
# Agents use V(realm) instead of population headcount when migrating.
# ─────────────────────────────────────────────────────────────────────────────

_GAMMA = 0.95   # discount factor
_ALPHA = 0.1    # TD learning rate


def update_bellman_values(state: SimState):
    """
    Update per-realm value estimates using TD(0) Bellman backup.
    V(realm) ← V(realm) + α [r + γ V(realm) − V(realm)]
             = V(realm) + α r  (since γ·V cancels in steady state)

    r is the mean wealth change of agents in that realm this tick.
    """
    # Initialise values
    for realm_name in state.realms:
        if realm_name not in state.realm_values:
            state.realm_values[realm_name] = 0.0

    # Compute mean reward per realm this tick
    realm_reward: dict[str, list[float]] = {r: [] for r in state.realms}
    for agent in state.agents.values():
        if agent.realm in realm_reward and agent.fitness_history:
            if len(agent.fitness_history) >= 2:
                delta = agent.fitness_history[-1] - agent.fitness_history[-2]
                realm_reward[agent.realm].append(delta)

    for realm_name in state.realms:
        rewards = realm_reward.get(realm_name, [])
        r = sum(rewards) / len(rewards) if rewards else 0.0
        v = state.realm_values[realm_name]
        # Bellman backup: V ← V + α (r + γV - V)
        state.realm_values[realm_name] = v + _ALPHA * (r + _GAMMA * v - v)


def best_realm_by_value(state: SimState) -> str:
    """Return realm name with highest Bellman value estimate."""
    from .agents import REALM_NAMES
    if not state.realm_values:
        return state.rng.choice(REALM_NAMES)
    return max(REALM_NAMES, key=lambda r: state.realm_values.get(r, 0.0))


# ─────────────────────────────────────────────────────────────────────────────
# 4. SELF-ORGANIZED CRITICALITY
# Track wealth "avalanches": when an agent's wealth drops sharply, it may
# cascade to neighbours (via reduced trading / staking).
# Monitor: distribution of single-tick wealth drops across all agents.
# Signature of SOC: power-law distribution of drop sizes.
# ─────────────────────────────────────────────────────────────────────────────

def detect_avalanche(state: SimState) -> float:
    """
    Compute the largest single-tick wealth drop across all agents.
    A large avalanche suggests a phase transition / market crash event.
    """
    max_drop = 0.0
    for agent in state.agents.values():
        if len(agent.fitness_history) >= 2:
            drop = agent.fitness_history[-2] - agent.fitness_history[-1]
            if drop > max_drop:
                max_drop = drop
    state.last_avalanche_size = max_drop
    return max_drop


def avalanche_distribution(state: SimState) -> dict[str, int]:
    """
    Return histogram of single-tick wealth drops (binned by magnitude).
    SOC signature: bin counts follow a power law P(s) ~ s^{-τ}.
    """
    drops = []
    for agent in state.agents.values():
        if len(agent.fitness_history) >= 2:
            drop = agent.fitness_history[-2] - agent.fitness_history[-1]
            if drop > 0:
                drops.append(drop)

    if not drops:
        return {}

    # Log-bin the drops
    bins = {"0-1": 0, "1-10": 0, "10-100": 0, "100-1000": 0, "1000+": 0}
    for d in drops:
        if d < 1:
            bins["0-1"] += 1
        elif d < 10:
            bins["1-10"] += 1
        elif d < 100:
            bins["10-100"] += 1
        elif d < 1000:
            bins["100-1000"] += 1
        else:
            bins["1000+"] += 1
    return bins


def is_near_critical(state: SimState) -> bool:
    """
    Heuristic: system is near critical when temperature is in the transition zone
    (neither too ordered nor too disordered) AND entropy is near maximum.
    Analogous to being near T_c in the Ising model.
    """
    n_agents = len(state.agents)
    max_entropy = math.log(n_agents) if n_agents > 1 else 1.0
    entropy_ratio = state.entropy / max_entropy if max_entropy > 0 else 0.0
    # Critical zone: moderate temperature (0.3–1.5) and entropy > 60% of max
    return 0.3 < state.temperature < 1.5 and entropy_ratio > 0.6


# ─────────────────────────────────────────────────────────────────────────────
# Combined update — called once per tick from engine
# ─────────────────────────────────────────────────────────────────────────────

def tick_dynamics(state: SimState):
    """Run all four theoretical dynamics for this tick."""
    update_thermodynamics(state)
    update_bellman_values(state)
    evolve_strategies(state)
    detect_avalanche(state)
