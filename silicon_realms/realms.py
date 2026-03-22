"""
Realm Tick Functions — Theory-Driven Differentiated Mechanics
=============================================================

Each realm is governed by a dominant theoretical framework:

  Compute  →  Replicator Dynamics (EGT)
    Mining strategies compete via fitness-proportional selection.
    Selection pressure increases with difficulty; fittest strategies
    earn disproportionate rewards (above-average grows, below shrinks).

  Memory   →  Statistical Mechanics
    Knowledge is an energy landscape.  Local temperature controls
    exploration (high T → random sharing) vs exploitation (low T →
    concentrated gains).  Entropy drives a shared knowledge pool
    that benefits long-tenure agents.

  Network  →  Control Theory (Bellman)
    Routing optimizes a per-realm value function via TD learning.
    Route efficiency grows when throughput improves; congestion
    penalizes overcrowding.  Agents earn proportional to learned
    routing quality.

  Information  →  Information Theory (Shannon)
    Agents are information channels with signal-to-noise ratios.
    Channel capacity C = log₂(1 + SNR) determines max reward rate.
    Mutual information between agents drives collaboration bonuses.
    Noise level evolves with wealth volatility; redundancy provides
    resilience but limits efficiency.

Cross-realm: SOC avalanches cascade — a large wealth drop in one
realm spills over as reduced rewards in neighbouring realms.
"""
from __future__ import annotations

import math

from .models import Agent, Realm, SimState
from .economy import mint, transfer


# ─── Compute Realm: Replicator Dynamics ──────────────────────────────────

def compute_tick(state: SimState, realm: Realm, agents: list[Agent]):
    """
    Replicator-dynamics mining.

    1. Compute per-strategy fitness (mean wealth of agents using that strategy).
    2. Selection pressure scales with difficulty: as difficulty grows, the
       gap between winning and losing strategies widens.
    3. Reward = base_reward * (strategy_fitness / mean_fitness) / difficulty.
       Agents in above-average strategies earn more; below-average earn less.
    4. Update realm state: dominant strategy, selection pressure, strategy fitness.
    """
    if not agents:
        return

    difficulty_growth = realm.params.get("difficulty_growth", 0.02)
    difficulty = 1 + difficulty_growth * state.tick

    # Per-strategy fitness in this realm
    strat_wealth: dict[str, list[float]] = {}
    for agent in agents:
        w = agent.balance + agent.staked
        strat_wealth.setdefault(agent.strategy, []).append(w)

    strat_mean = {s: sum(ws) / len(ws) for s, ws in strat_wealth.items()}
    all_fitness = [w for ws in strat_wealth.values() for w in ws]
    mean_fitness = sum(all_fitness) / len(all_fitness) if all_fitness else 1.0

    # Update realm-level state
    realm.strategy_fitness = strat_mean
    realm.dominant_strategy = max(strat_mean, key=strat_mean.get) if strat_mean else ""
    realm.selection_pressure = min(5.0, 1.0 + difficulty_growth * state.tick * 0.5)

    for agent in agents:
        if agent.energy <= 0:
            continue

        agent_fitness = agent.balance + agent.staked
        # Replicator reward: proportional to fitness relative to mean
        # fitness_ratio > 1 → above average → amplified reward
        # fitness_ratio < 1 → below average → reduced reward
        fitness_ratio = (agent_fitness + 1) / (mean_fitness + 1)

        # Selection pressure amplifies the gap: ratio^pressure
        amplified = fitness_ratio ** realm.selection_pressure
        reward = realm.base_reward * amplified / difficulty

        # Probability of successful mining scales with energy
        if state.rng.random() < agent.energy / 100:
            mint(state, agent.id, reward)
            agent.energy -= 1


# ─── Memory Realm: Statistical Mechanics ─────────────────────────────────

def memory_tick(state: SimState, realm: Realm, agents: list[Agent]):
    """
    Statistical-mechanics knowledge economy.

    1. Compute local temperature (wealth dispersion among memory agents)
       and local entropy (Shannon entropy of wealth distribution).
    2. Knowledge pool: a shared reservoir that grows with agent contributions
       and decays over time.  High-entropy state → more sharing → pool grows.
    3. Reward has two components:
       a) Individual: Boltzmann-weighted by agent's "knowledge energy" (tenure).
          Low T → concentrated on high-tenure agents (exploitation).
          High T → spread more evenly (exploration).
       b) Collective: share of the knowledge pool proportional to tenure.
    4. Agents trade knowledge when temperature is high (thermal fluctuations).
    """
    if not agents:
        return

    decay_rate = realm.params.get("decay_rate", 0.01)

    # ── Local thermodynamics ──
    wealths = [a.balance + a.staked for a in agents if a.balance + a.staked > 0]
    if len(wealths) >= 2:
        mean_w = sum(wealths) / len(wealths)
        if mean_w > 1e-9:
            variance = sum((w - mean_w) ** 2 for w in wealths) / len(wealths)
            realm.realm_temperature = math.sqrt(variance) / mean_w
        else:
            realm.realm_temperature = 1.0
    else:
        realm.realm_temperature = 1.0

    total_w = sum(wealths)
    if total_w > 1e-9:
        realm.realm_entropy = -sum(
            (w / total_w) * math.log(w / total_w)
            for w in wealths if w > 1e-12
        )
    else:
        realm.realm_entropy = 0.0

    # ── Knowledge pool dynamics ──
    # Pool grows with contributions (high entropy → more sharing)
    # Pool decays naturally
    entropy_factor = min(2.0, 1.0 + realm.realm_entropy * 0.3)
    realm.knowledge_pool *= (1 - decay_rate)  # decay
    pool_contribution = realm.base_reward * 0.2 * entropy_factor * len(agents)
    realm.knowledge_pool += pool_contribution

    # ── Per-agent rewards ──
    T = max(0.1, realm.realm_temperature)  # clamp to avoid division by zero

    for agent in agents:
        if agent.energy <= 0:
            continue

        age = max(1, state.tick - agent.created_tick)
        # "Knowledge energy" — tenure-based, with decay
        knowledge_energy = realm.base_reward * (1 - decay_rate) ** age

        # Boltzmann factor: P ∝ exp(-E/T) where low E = high knowledge
        # Invert: high tenure → low "energy cost" → higher probability
        boltzmann_weight = math.exp(-1.0 / (age * T + 1e-9))

        # Individual reward: Boltzmann-weighted knowledge value
        individual_reward = knowledge_energy * boltzmann_weight
        if individual_reward > 0.01:
            mint(state, agent.id, individual_reward)

        # Collective reward: share of knowledge pool weighted by tenure
        if realm.knowledge_pool > 0 and len(agents) > 0:
            tenure_share = age / sum(
                max(1, state.tick - a.created_tick) for a in agents
            )
            pool_reward = realm.knowledge_pool * tenure_share * 0.05
            if pool_reward > 0.01:
                mint(state, agent.id, pool_reward)

        agent.energy -= 1

    # ── Thermal trading: high T → more random exchanges ──
    trade_probability = min(0.4, 0.05 + realm.realm_temperature * 0.15)
    if len(agents) > 1:
        for agent in agents:
            if state.rng.random() < trade_probability and agent.balance > 1:
                partner = state.rng.choice([a for a in agents if a.id != agent.id])
                trade_amount = min(agent.balance * 0.05, 5.0)
                if trade_amount > 0:
                    transfer(state, agent.id, partner.id, trade_amount)


# ─── Network Realm: Control Theory (Bellman) ─────────────────────────────

def network_tick(state: SimState, realm: Realm, agents: list[Agent]):
    """
    Bellman-optimal routing economy.

    1. Congestion: population relative to optimal capacity.  Over-capacity
       reduces per-agent reward (diminishing returns).
    2. Route efficiency: a learned value (TD update) that improves when
       throughput increases and degrades when it decreases.
    3. Reward = (base_reward * route_efficiency - congestion_penalty)
       + routing fee bonus scaled by efficiency.
    4. Throughput = total tokens flowing through network this tick.
    """
    if not agents:
        return

    routing_fee = realm.params.get("routing_fee", 0.05)
    optimal_load = realm.capacity * 0.6  # sweet spot: 60% of capacity

    # ── Congestion ──
    n = len(agents)
    if n > optimal_load:
        realm.congestion = min(0.8, (n - optimal_load) / (realm.capacity - optimal_load + 1))
    else:
        realm.congestion = 0.0

    # ── Throughput: sum of all active agent wealth (proxy for traffic) ──
    throughput = sum(a.balance for a in agents if a.energy > 0)
    realm.throughput_history.append(throughput)
    if len(realm.throughput_history) > 20:
        realm.throughput_history.pop(0)

    # ── TD(0) update of route_efficiency ──
    # r = throughput improvement (reward signal)
    if len(realm.throughput_history) >= 2:
        delta = realm.throughput_history[-1] - realm.throughput_history[-2]
        # Normalize reward signal
        r = delta / (abs(realm.throughput_history[-2]) + 1e-9)
        r = max(-1.0, min(1.0, r))  # clamp
    else:
        r = 0.0

    alpha = 0.15   # learning rate
    gamma = 0.9    # discount
    v = realm.route_efficiency
    # Bellman backup: V ← V + α(r + γV − V)
    realm.route_efficiency = max(0.1, min(3.0, v + alpha * (r + gamma * v - v)))

    # ── Per-agent rewards ──
    congestion_penalty = realm.congestion * realm.base_reward * 0.5

    for agent in agents:
        if agent.energy <= 0:
            continue

        # Base routing reward scaled by learned efficiency
        base = realm.base_reward * realm.route_efficiency / max(1, n)
        # Subtract congestion cost
        reward = max(0.01, base - congestion_penalty / max(1, n))

        mint(state, agent.id, reward)

        # Routing fee bonus: proportional to total supply and efficiency
        bonus = state.total_supply * routing_fee * 0.001 * realm.route_efficiency / max(1, n)
        if bonus > 0:
            mint(state, agent.id, bonus)

        agent.energy -= 1


# ─── Information Realm: Information Theory (Shannon) ─────────────────────

def information_tick(state: SimState, realm: Realm, agents: list[Agent]):
    """
    Shannon information-theoretic economy.

    1. Each agent is an information channel.  Signal = wealth, Noise = wealth
       volatility (from fitness_history).  SNR = signal / noise.
    2. Channel capacity C = log₂(1 + SNR) — limits the max reward rate.
    3. Mutual information: agents with similar wealth profiles share information
       efficiently → collaboration bonus.
    4. Redundancy: when many agents carry similar information, marginal value
       decreases (diminishing returns from duplication).
    5. Realm noise evolves: high wealth variance → high noise → lower capacity.
    """
    if not agents:
        return

    base_noise = realm.params.get("base_noise", 0.5)

    # ── Realm-wide noise: driven by wealth volatility ──
    volatilities = []
    for a in agents:
        if len(a.fitness_history) >= 2:
            diffs = [abs(a.fitness_history[i] - a.fitness_history[i - 1])
                     for i in range(1, len(a.fitness_history))]
            volatilities.append(sum(diffs) / len(diffs))
        else:
            volatilities.append(base_noise)

    realm.noise_level = max(0.01, sum(volatilities) / len(volatilities)) if volatilities else base_noise

    # ── Per-agent SNR and channel capacity ──
    agent_capacity = {}
    for a in agents:
        signal = max(0.01, a.balance + a.staked)
        # Individual noise: agent's own volatility
        if len(a.fitness_history) >= 2:
            diffs = [abs(a.fitness_history[i] - a.fitness_history[i - 1])
                     for i in range(1, len(a.fitness_history))]
            agent_noise = max(0.01, sum(diffs) / len(diffs))
        else:
            agent_noise = base_noise
        snr = signal / agent_noise
        agent_capacity[a.id] = math.log2(1 + snr)

    # ── Aggregate channel capacity ──
    total_capacity = sum(agent_capacity.values())
    realm.channel_capacity = total_capacity / len(agents) if agents else 1.0

    # ── Mutual information: pairwise wealth similarity ──
    # MI is high when agents have correlated wealth levels
    wealths = [a.balance + a.staked for a in agents]
    total_w = sum(wealths) + 1e-9
    mi = 0.0
    if len(agents) >= 2:
        # Approximate MI via normalized wealth correlation
        mean_w = total_w / len(agents)
        for i in range(len(agents)):
            for j in range(i + 1, min(i + 5, len(agents))):  # limit pairs for efficiency
                wi = wealths[i] / total_w
                wj = wealths[j] / total_w
                # Joint vs marginal: higher when wealth is similar
                joint = (wi + wj) / 2
                if joint > 1e-12:
                    mi += joint * math.log2(joint / (wi * wj + 1e-12) + 1e-12)
        mi = max(0.0, mi)
    realm.mutual_information = mi

    # ── Redundancy: how concentrated/duplicated the wealth distribution is ──
    # High redundancy when agents are very similar (low diversity)
    if len(wealths) >= 2:
        mean_w = sum(wealths) / len(wealths)
        variance = sum((w - mean_w) ** 2 for w in wealths) / len(wealths)
        cv = math.sqrt(variance) / (mean_w + 1e-9)  # coefficient of variation
        # Low CV = high redundancy (everyone similar), high CV = low redundancy
        realm.redundancy = max(0.0, 1.0 - min(1.0, cv))
    else:
        realm.redundancy = 1.0

    # ── Per-agent rewards ──
    # Efficiency factor: moderate redundancy is good (resilience), too much is wasteful
    # Optimal redundancy ~ 0.5 (bell curve penalty)
    redundancy_factor = 1.0 - 2.0 * (realm.redundancy - 0.5) ** 2

    for agent in agents:
        if agent.energy <= 0:
            continue

        # Channel capacity reward: C determines max reward rate
        capacity = agent_capacity.get(agent.id, 1.0)
        capacity_reward = realm.base_reward * capacity / (math.log2(1 + 100 / base_noise) + 1e-9)

        # Mutual information bonus: collaboration reward
        mi_bonus = realm.mutual_information * 0.1 * realm.base_reward / max(1, len(agents))

        # Apply redundancy factor
        reward = max(0.01, (capacity_reward + mi_bonus) * max(0.3, redundancy_factor))

        if state.rng.random() < agent.energy / 100:
            mint(state, agent.id, reward)
            agent.energy -= 1


# ─── SOC Avalanche Cascade ──────────────────────────────────────────────

def apply_avalanche_spillover(state: SimState):
    """
    Cross-realm avalanche cascade.

    When a large wealth drop (avalanche) is detected in any realm,
    it spills over as reduced realm effectiveness in neighbouring realms.
    This creates correlated stress across the system — a signature of SOC.
    """
    if state.last_avalanche_size < 10:
        return  # only significant avalanches cascade

    # Find which realm the avalanche originated in
    for agent in state.agents.values():
        if len(agent.fitness_history) >= 2:
            drop = agent.fitness_history[-2] - agent.fitness_history[-1]
            if abs(drop - state.last_avalanche_size) < 0.01:
                source_realm = agent.realm
                break
    else:
        return

    # Cascade: other realms absorb a fraction of the shock
    cascade_fraction = min(0.3, state.last_avalanche_size / 1000)
    for realm_name, realm in state.realms.items():
        if realm_name == source_realm:
            realm.avalanche_exposure = state.last_avalanche_size
        else:
            realm.avalanche_exposure = state.last_avalanche_size * cascade_fraction


# ─── Migration with theory-aware destination ────────────────────────────

def migrate_agent(state: SimState, agent: Agent, target_realm: str) -> bool:
    if target_realm == agent.realm:
        return False

    target = state.realms.get(target_realm)
    if target is None:
        return False

    # Check capacity
    pop = sum(1 for a in state.agents.values() if a.realm == target_realm)
    if pop >= target.capacity:
        return False

    migration_cost = 5.0
    if agent.balance < migration_cost:
        return False

    agent.balance -= migration_cost
    state.total_supply -= migration_cost  # migration cost is burned
    state.ledger.record(state.tick, agent.id, "burned", migration_cost, "fee")

    agent.realm = target_realm
    agent.migration_cooldown = 5
    return True


REALM_TICK_FNS = {
    "compute": compute_tick,
    "memory": memory_tick,
    "network": network_tick,
    "information": information_tick,
}
