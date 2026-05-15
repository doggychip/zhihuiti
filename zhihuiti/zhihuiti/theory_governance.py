"""Theory-derived governance regimes.

Maps Ryan's synthesized theories (cross-domain collisions) to concrete
agent governance parameters. Each theory becomes a "policy regime" that
configures cull thresholds, messaging/lending behavior, and attention
allocation across the three realms.

These extend the existing THEORIES dict in collision.py.
"""
from __future__ import annotations


# Each regime derived from a Ryan's Theory: how does the theoretical insight
# translate to concrete agent-system parameters?
THEORY_REGIMES = {
    # ── Active Inference × World Models ──
    # Agents minimize prediction error. Reward those whose predictions match
    # actual outcomes. Strong messaging (agents share predictions). Research-heavy.
    "active_inference": {
        "label": "🧠 Active Inference",
        "description": (
            "Brain IS world model. Agents predict outcomes, get rewarded for "
            "accuracy, share predictions. Surprise = cost; predictability = fitness."
        ),
        "parent_theories": ["Active Inference", "World Models / Model-Based RL"],
        "cull_threshold": 0.40,
        "promote_threshold": 0.80,
        "messaging": True,
        "lending": True,
        "attention": {"research": 0.50, "execution": 0.35, "central": 0.15},
        "scoring_modifier": "prediction_accuracy_bonus",
        "novel_mechanic": "agents emit predictions; correct ones boost score, wrong ones drain budget",
    },

    # ── Kin Selection × Shapley ──
    # Bloodline-aware: same lineage supports each other. Hamilton's rule (rb > c).
    # Promotion considers contribution to parent's score.
    "kin_selection": {
        "label": "🩸 Kin Selection",
        "description": (
            "Hamilton's rule: rb > c. Agents support same-bloodline siblings, "
            "inclusive fitness shapes promotion. Lending within lineage only."
        ),
        "parent_theories": ["Hamilton's Rule / Kin Selection", "Shapley Value"],
        "cull_threshold": 0.20,  # forgiving for same bloodline
        "promote_threshold": 0.75,
        "messaging": True,
        "lending": True,
        "attention": {"research": 0.45, "execution": 0.40, "central": 0.15},
        "scoring_modifier": "inclusive_fitness",
        "novel_mechanic": "score includes bloodline contribution weighted by relatedness",
    },

    # ── Group Selection × Price Equation ──
    # Multi-level: realm-level fitness vs individual-level. Promotes realms,
    # not just agents.
    "price_equation": {
        "label": "👥 Multilevel Selection",
        "description": (
            "Price decomposition: Δx = Cov(W_group, x) + E[Cov(W_individual, x)]. "
            "Both realm-level and individual fitness matter. Heavy central coordination."
        ),
        "parent_theories": ["Price Equation (Multilevel Selection)", "Group Selection"],
        "cull_threshold": 0.30,
        "promote_threshold": 0.78,
        "messaging": True,
        "lending": True,
        "attention": {"research": 0.35, "execution": 0.35, "central": 0.30},
        "scoring_modifier": "multilevel_covariance",
        "novel_mechanic": "realm-wide score affects all agents in that realm",
    },

    # ── Hawk-Dove × Nash ──
    # Mixed strategy ESS. Some agents are aggressive (high bids), some peaceful
    # (cooperative). Population converges to V/C ratio.
    "hawk_dove": {
        "label": "🦅 Hawk-Dove ESS",
        "description": (
            "Mixed strategy equilibrium: x_hawk* = V/C. Population maintains "
            "diversity of aggression levels. Communication on, resource lending off."
        ),
        "parent_theories": ["Hawk-Dove Game", "Nash Equilibrium"],
        "cull_threshold": 0.35,
        "promote_threshold": 0.85,
        "messaging": True,
        "lending": False,
        "attention": {"research": 0.30, "execution": 0.50, "central": 0.20},
        "scoring_modifier": "frequency_dependent",
        "novel_mechanic": "agent bids are penalized when too many compete for same task",
    },

    # ── Regret Minimization × Bandit ──
    # No-regret learning: cull based on accumulated regret vs hindsight-best.
    # High exploration budget.
    "regret_min": {
        "label": "📉 No-Regret Learning",
        "description": (
            "Cull by hindsight regret: ∑(best_possible − actual). "
            "High research allocation for exploration. Sublinear regret bound."
        ),
        "parent_theories": ["Regret Minimization", "Multi-Armed Bandit / UCB"],
        "cull_threshold": 0.30,
        "promote_threshold": 0.80,
        "messaging": True,
        "lending": True,
        "attention": {"research": 0.60, "execution": 0.25, "central": 0.15},
        "scoring_modifier": "regret_penalty",
        "novel_mechanic": "agents tracked against hindsight-optimal counterfactual",
    },

    # ── Moran × Wright-Fisher ──
    # Stochastic birth-death proportional to fitness. Finite population fixation.
    # Even attention.
    "moran_process": {
        "label": "🎲 Moran Process",
        "description": (
            "Stochastic birth-death: P(reproduce) ∝ fitness. "
            "Random culling weighted by inverse fitness. Population size conserved."
        ),
        "parent_theories": ["Moran Process", "Wright-Fisher / Population Genetics"],
        "cull_threshold": 0.30,
        "promote_threshold": 0.75,
        "messaging": False,
        "lending": False,
        "attention": {"research": 0.40, "execution": 0.45, "central": 0.15},
        "scoring_modifier": "stochastic_fitness",
        "novel_mechanic": "fixed population size; each cycle one birth, one death",
    },

    # ── Free Energy Principle × Replicator ──
    # Variational free energy minimization. Selection toward predictive accuracy.
    "free_energy": {
        "label": "🌀 Free Energy Principle",
        "description": (
            "Agents minimize variational free energy F = E_q[log q − log p]. "
            "Selection toward predictive models. Cooperation through shared world model."
        ),
        "parent_theories": ["Free Energy Principle (Friston)", "Replicator Dynamics (EGT)"],
        "cull_threshold": 0.35,
        "promote_threshold": 0.82,
        "messaging": True,
        "lending": True,
        "attention": {"research": 0.55, "execution": 0.30, "central": 0.15},
        "scoring_modifier": "free_energy_minimization",
        "novel_mechanic": "agents that better predict task outcomes survive",
    },

    # ── Mean-Field Game × Mechanism Design ──
    # Large-population games where individual best-response converges to
    # mean-field equilibrium. Mechanism designer (treasury) sets incentives.
    "mean_field_mechanism": {
        "label": "📐 Mean-Field Mechanism",
        "description": (
            "Each agent best-responds to population mean. Treasury acts as "
            "mechanism designer setting auction rules to elicit truthful bids."
        ),
        "parent_theories": ["Mean-Field Game", "Mechanism Design / Auction Theory"],
        "cull_threshold": 0.32,
        "promote_threshold": 0.80,
        "messaging": True,
        "lending": False,
        "attention": {"research": 0.40, "execution": 0.40, "central": 0.20},
        "scoring_modifier": "mean_field_response",
        "novel_mechanic": "agent bid corrected by population-mean bid; treasury tunes mechanism",
    },
}


def get_regime(name: str) -> dict | None:
    """Get a theory-derived governance regime by name."""
    return THEORY_REGIMES.get(name)


def all_regimes() -> dict[str, dict]:
    """Return all theory-derived regimes."""
    return dict(THEORY_REGIMES)


def merge_into_theories(theories_dict: dict) -> dict:
    """Merge theory regimes into an existing THEORIES dict.

    Used by collision.py to expose theory-derived regimes alongside the
    classical 6 (darwinian, mutualist, hybrid, elitist, ecosystem, social_contract).
    """
    merged = dict(theories_dict)
    merged.update(THEORY_REGIMES)
    return merged


def apply_scoring_modifier(
    modifier: str,
    agent_state: dict,
    task_score: float,
    context: dict | None = None,
) -> float:
    """Apply a theory-specific scoring adjustment to a base task score.

    Args:
        modifier: One of the scoring_modifier strings defined in THEORY_REGIMES
        agent_state: Dict with agent's bloodline, predictions, history, etc.
        task_score: Base score from inspection (0.0-1.0)
        context: Optional context dict (other agents, population stats, etc.)

    Returns:
        Adjusted score, bounded to [0, 1].
    """
    context = context or {}

    if modifier == "prediction_accuracy_bonus":
        # If agent emitted predictions and they matched, boost score
        pred_acc = agent_state.get("prediction_accuracy", 0.5)
        return min(1.0, task_score * (0.7 + 0.6 * pred_acc))

    if modifier == "inclusive_fitness":
        # Score includes weighted bloodline contribution
        bloodline_avg = agent_state.get("bloodline_avg_score", task_score)
        r = agent_state.get("relatedness", 0.25)  # avg relatedness
        return min(1.0, task_score + r * bloodline_avg * 0.3)

    if modifier == "multilevel_covariance":
        # Score blends individual + realm performance
        realm_avg = context.get("realm_avg_score", task_score)
        return min(1.0, 0.6 * task_score + 0.4 * realm_avg)

    if modifier == "frequency_dependent":
        # Penalize over-competition: if many agents bid on same task, score discounted
        competition = context.get("competing_agents_on_task", 1)
        penalty = 1.0 / (1.0 + 0.1 * (competition - 1))
        return min(1.0, task_score * penalty)

    if modifier == "regret_penalty":
        # Subtract regret accumulator
        regret = agent_state.get("cumulative_regret", 0.0)
        return max(0.0, task_score - 0.05 * regret)

    if modifier == "stochastic_fitness":
        # Add small noise (stochastic process)
        import random
        return max(0.0, min(1.0, task_score + random.gauss(0, 0.05)))

    if modifier == "free_energy_minimization":
        # Reward agents that minimize KL divergence between model and outcome
        free_energy = agent_state.get("free_energy", 0.5)  # lower is better
        return min(1.0, task_score * (1.5 - free_energy))

    if modifier == "mean_field_response":
        # Score based on deviation from mean response (rewarding marginal value)
        mean_response = context.get("population_mean_score", task_score)
        if mean_response > 0:
            return min(1.0, task_score * (task_score / mean_response))
        return task_score

    return task_score  # unknown modifier: no change
