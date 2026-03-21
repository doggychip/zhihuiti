from __future__ import annotations

import random
from pathlib import Path

import yaml

from .models import Realm, SimState
from .agents import create_agents, agent_decide, agent_act
from .economy import distribute_staking_rewards, get_summary
from .realms import REALM_TICK_FNS
from .visualization import plot_simulation


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def init_state(config: dict) -> SimState:
    seed = config.get("simulation", {}).get("seed", 42)
    state = SimState(
        rng=random.Random(seed),
        config=config,
    )

    for name, params in config.get("realms", {}).items():
        state.realms[name] = Realm(
            name=name,
            capacity=params.get("capacity", 50),
            base_reward=params.get("base_reward", 10),
            params=params,
        )

    return state


def mint_tick(state: SimState):
    """Distribute new tokens across active agents."""
    from .economy import mint

    mint_rate = state.config.get("economy", {}).get("mint_rate", 50)
    active_agents = [a for a in state.agents.values() if a.energy > 0]
    if not active_agents:
        return

    per_agent = mint_rate / len(active_agents)
    for agent in active_agents:
        mint(state, agent.id, per_agent)


def update_energy(state: SimState):
    """Agents with no energy and no balance are eliminated (set to minimal state)."""
    for agent in state.agents.values():
        if agent.energy <= 0 and agent.balance > 1:
            # Spend tokens to recharge
            cost = min(agent.balance, 5.0)
            agent.balance -= cost
            state.total_supply -= cost
            agent.energy = min(100, int(cost * 10))


def print_summary(state: SimState):
    summary = get_summary(state)
    print(f"\n--- Tick {summary['tick']:>4d} ---")
    print(f"  Supply: {summary['total_supply']:.0f}  "
          f"Circulating: {summary['circulating']:.0f}  "
          f"Staked: {summary['total_staked']:.0f}  "
          f"Gini: {summary['gini']:.3f}")
    print(f"  Realms: {summary['realm_population']}")
    print(f"  Richest: {summary['richest']}  Poorest: {summary['poorest']}")


def print_final_report(state: SimState):
    summary = get_summary(state)
    print("\n" + "=" * 50)
    print("  SILICON REALMS - FINAL REPORT")
    print("=" * 50)
    print(f"  Ticks simulated: {state.tick + 1}")
    print(f"  Total supply:    {summary['total_supply']:.0f} SiCoin")
    print(f"  Circulating:     {summary['circulating']:.0f} SiCoin")
    print(f"  Total staked:    {summary['total_staked']:.0f} SiCoin")
    print(f"  Gini coefficient: {summary['gini']:.4f}")
    print(f"  Transactions:    {len(state.ledger.transactions)}")
    print()

    # Strategy breakdown
    strat_wealth = {}
    strat_count = {}
    for a in state.agents.values():
        w = a.balance + a.staked
        strat_wealth[a.strategy] = strat_wealth.get(a.strategy, 0) + w
        strat_count[a.strategy] = strat_count.get(a.strategy, 0) + 1

    print("  Strategy performance (avg wealth):")
    for s in sorted(strat_wealth):
        avg = strat_wealth[s] / strat_count[s] if strat_count[s] else 0
        print(f"    {s:>10s}: {avg:>8.1f} SiCoin  ({strat_count[s]} agents)")

    print()
    print(f"  Richest: {summary['richest']}")
    print(f"  Poorest: {summary['poorest']}")
    print(f"  Realm population: {summary['realm_population']}")
    print("=" * 50)


def collect_history(state: SimState) -> dict:
    """Collect a snapshot of the current tick for visualization."""
    summary = get_summary(state)
    # Strategy average wealth
    strat_wealth = {}
    strat_count = {}
    for a in state.agents.values():
        w = a.balance + a.staked
        strat_wealth[a.strategy] = strat_wealth.get(a.strategy, 0) + w
        strat_count[a.strategy] = strat_count.get(a.strategy, 0) + 1
    strat_avg = {s: strat_wealth[s] / strat_count[s] for s in strat_wealth}

    return {
        "total_supply": summary["total_supply"],
        "circulating": summary["circulating"],
        "staked": summary["total_staked"],
        "gini": summary["gini"],
        "realm_population": dict(summary["realm_population"]),
        "strategy_wealth": strat_avg,
    }


def run(config_path: str, plot: bool = True) -> SimState:
    config = load_config(config_path)
    state = init_state(config)
    create_agents(config, state)

    ticks = config.get("simulation", {}).get("ticks", 100)
    log_interval = config.get("simulation", {}).get("log_interval", 10)

    print("Silicon Realms - Three-Realm Agent Civilization")
    print(f"Running {ticks} ticks with {len(state.agents)} agents...\n")

    history = {
        "ticks": [],
        "total_supply": [],
        "circulating": [],
        "staked": [],
        "gini": [],
        "realm_population": [],
        "strategy_wealth": [],
    }

    for tick in range(ticks):
        state.tick = tick

        # 1. Mint new tokens
        mint_tick(state)

        # 2. Agent decisions and actions
        for agent in list(state.agents.values()):
            action = agent_decide(state, agent)
            agent_act(state, agent, action)

        # 3. Realm ticks
        for realm_name, realm in state.realms.items():
            tick_fn = REALM_TICK_FNS.get(realm_name)
            if tick_fn:
                agents_in_realm = [a for a in state.agents.values() if a.realm == realm_name]
                tick_fn(state, realm, agents_in_realm)

        # 4. Staking rewards
        distribute_staking_rewards(state)

        # 5. Energy management
        update_energy(state)

        # 6. Collect history snapshot
        snapshot = collect_history(state)
        history["ticks"].append(tick)
        for key in ("total_supply", "circulating", "staked", "gini",
                     "realm_population", "strategy_wealth"):
            history[key].append(snapshot[key])

        # 7. Periodic summary
        if tick % log_interval == 0:
            print_summary(state)

    print_final_report(state)

    if plot:
        plot_simulation(history)

    return state
