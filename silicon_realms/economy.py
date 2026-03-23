from __future__ import annotations

from .models import SimState


def mint(state: SimState, agent_id: str, amount: float):
    agent = state.agents[agent_id]
    agent.balance += amount
    state.total_supply += amount
    state.ledger.record(state.tick, "system", agent_id, amount, "mint")


def transfer(state: SimState, sender_id: str, receiver_id: str, amount: float) -> bool:
    sender = state.agents[sender_id]
    fee_rate = state.config.get("economy", {}).get("transfer_fee", 0.01)
    fee = amount * fee_rate
    total_cost = amount + fee

    if sender.balance < total_cost:
        return False

    receiver = state.agents[receiver_id]
    sender.balance -= total_cost
    receiver.balance += amount
    state.total_supply -= fee  # fees are burned

    state.ledger.record(state.tick, sender_id, receiver_id, amount, "transfer")
    if fee > 0:
        state.ledger.record(state.tick, sender_id, "burned", fee, "fee")

    return True


def stake(state: SimState, agent_id: str, amount: float) -> bool:
    agent = state.agents[agent_id]
    stake_min = state.config.get("economy", {}).get("stake_min", 10)

    if amount < stake_min or agent.balance < amount:
        return False

    agent.balance -= amount
    agent.staked += amount
    state.ledger.record(state.tick, agent_id, "staking_pool", amount, "stake")
    return True


def unstake(state: SimState, agent_id: str, amount: float) -> bool:
    agent = state.agents[agent_id]
    if agent.staked < amount:
        return False

    agent.staked -= amount
    agent.balance += amount
    state.ledger.record(state.tick, "staking_pool", agent_id, amount, "unstake")
    return True


def distribute_staking_rewards(state: SimState):
    rate = state.config.get("economy", {}).get("stake_reward_rate", 0.03)
    for agent in state.agents.values():
        if agent.staked > 0:
            reward = agent.staked * rate
            agent.balance += reward
            state.total_supply += reward
            state.ledger.record(state.tick, "system", agent.id, reward, "reward")


def get_summary(state: SimState) -> dict:
    balances = [a.balance + a.staked for a in state.agents.values()]
    total_staked = sum(a.staked for a in state.agents.values())
    total_balance = sum(a.balance for a in state.agents.values())

    # Gini coefficient
    gini = 0.0
    n = len(balances)
    if n > 0 and sum(balances) > 0:
        sorted_b = sorted(balances)
        cumulative = 0.0
        for i, b in enumerate(sorted_b):
            cumulative += b
            gini += (2 * (i + 1) - n - 1) * b
        gini /= n * sum(sorted_b)

    richest = max(state.agents.values(), key=lambda a: a.balance + a.staked, default=None)
    poorest = min(state.agents.values(), key=lambda a: a.balance + a.staked, default=None)

    realm_pop = {}
    for a in state.agents.values():
        realm_pop[a.realm] = realm_pop.get(a.realm, 0) + 1

    return {
        "tick": state.tick,
        "total_supply": state.total_supply,
        "circulating": total_balance,
        "total_staked": total_staked,
        "gini": round(gini, 4),
        "richest": f"{richest.name} ({richest.balance + richest.staked:.1f})" if richest else "N/A",
        "poorest": f"{poorest.name} ({poorest.balance + poorest.staked:.1f})" if poorest else "N/A",
        "realm_population": realm_pop,
    }
