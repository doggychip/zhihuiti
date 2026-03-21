from __future__ import annotations

from .models import Agent, Realm, SimState
from .economy import mint, transfer


def compute_tick(state: SimState, realm: Realm, agents: list[Agent]):
    difficulty_growth = realm.params.get("difficulty_growth", 0.02)
    reward = realm.base_reward / (1 + difficulty_growth * state.tick)

    for agent in agents:
        if agent.energy > 0 and state.rng.random() < agent.energy / 100:
            mint(state, agent.id, reward)
            agent.energy -= 1


def memory_tick(state: SimState, realm: Realm, agents: list[Agent]):
    decay_rate = realm.params.get("decay_rate", 0.01)

    for agent in agents:
        if agent.energy <= 0:
            continue

        # Data value decays but agents earn based on accumulated knowledge
        age = max(1, state.tick - agent.created_tick)
        data_value = realm.base_reward * (1 - decay_rate) ** age
        if data_value > 0.01:
            mint(state, agent.id, data_value)

        # Memory agents occasionally trade data with each other
        if len(agents) > 1 and state.rng.random() < 0.1:
            partner = state.rng.choice([a for a in agents if a.id != agent.id])
            trade_amount = min(agent.balance * 0.05, 5.0)
            if trade_amount > 0:
                transfer(state, agent.id, partner.id, trade_amount)

        agent.energy -= 1


def network_tick(state: SimState, realm: Realm, agents: list[Agent]):
    routing_fee = realm.params.get("routing_fee", 0.05)

    if not agents:
        return

    # Network agents earn by facilitating traffic; reward split among all
    reward_per_agent = realm.base_reward / max(1, len(agents))

    for agent in agents:
        if agent.energy > 0:
            mint(state, agent.id, reward_per_agent)
            # Earn routing fees proportional to network activity
            bonus = state.total_supply * routing_fee * 0.001 / max(1, len(agents))
            if bonus > 0:
                mint(state, agent.id, bonus)
            agent.energy -= 1


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
}
