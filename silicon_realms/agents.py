from __future__ import annotations

from .models import Agent, SimState
from .economy import stake, unstake
from .realms import migrate_agent


STRATEGIES = ["greedy", "staker", "nomad", "balanced"]
REALM_NAMES = ["compute", "memory", "network"]

AGENT_PREFIXES = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
    "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi",
    "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
    "Apex", "Core", "Flux", "Grid", "Hexa", "Ion",
]


def create_agents(config: dict, state: SimState):
    count = config.get("agents", {}).get("initial_count", 30)
    initial_balance = config["economy"]["initial_supply"] / count

    for i in range(count):
        name = AGENT_PREFIXES[i % len(AGENT_PREFIXES)]
        if i >= len(AGENT_PREFIXES):
            name = f"{name}-{i // len(AGENT_PREFIXES)}"

        realm = REALM_NAMES[i % len(REALM_NAMES)]
        strategy = state.rng.choice(STRATEGIES)

        agent = Agent(
            id=f"agent_{i:03d}",
            name=name,
            realm=realm,
            balance=initial_balance,
            strategy=strategy,
            created_tick=0,
        )
        state.agents[agent.id] = agent
        state.total_supply += initial_balance
        state.ledger.record(0, "system", agent.id, initial_balance, "mint")


def agent_decide(state: SimState, agent: Agent) -> str:
    if agent.energy <= 0:
        return "rest"

    if agent.migration_cooldown > 0:
        agent.migration_cooldown -= 1

    strategy = agent.strategy

    if strategy == "greedy":
        return "work"

    elif strategy == "staker":
        stake_min = state.config.get("economy", {}).get("stake_min", 10)
        if agent.balance >= stake_min * 2 and agent.staked < agent.balance:
            return "stake"
        return "work"

    elif strategy == "nomad":
        if agent.migration_cooldown <= 0 and state.rng.random() < 0.2:
            return "migrate"
        return "work"

    else:  # balanced
        r = state.rng.random()
        stake_min = state.config.get("economy", {}).get("stake_min", 10)
        if r < 0.3 and agent.balance >= stake_min * 2:
            return "stake"
        elif r < 0.35 and agent.staked > 0:
            return "unstake"
        elif r < 0.4 and agent.migration_cooldown <= 0:
            return "migrate"
        else:
            return "work"


def agent_act(state: SimState, agent: Agent, action: str):
    if action == "work":
        # Work is handled by realm ticks
        pass

    elif action == "stake":
        amount = agent.balance * 0.3
        stake(state, agent.id, amount)

    elif action == "unstake":
        amount = agent.staked * 0.5
        unstake(state, agent.id, amount)

    elif action == "migrate":
        # Use Bellman value estimates if available, else fall back to population
        if state.realm_values:
            from .dynamics import best_realm_by_value
            best_realm = best_realm_by_value(state)
        else:
            realm_pops = {}
            for a in state.agents.values():
                realm_pops[a.realm] = realm_pops.get(a.realm, 0) + 1
            best_realm = min(REALM_NAMES, key=lambda r: realm_pops.get(r, 0))
        migrate_agent(state, agent, best_realm)

    elif action == "rest":
        # Resting recovers energy if agent has tokens
        if agent.balance > 1:
            agent.energy = min(100, agent.energy + 10)
            agent.balance -= 1
            state.total_supply -= 1
            state.ledger.record(state.tick, agent.id, "burned", 1, "fee")
