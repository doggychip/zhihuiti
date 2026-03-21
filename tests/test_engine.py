import tempfile
import os
import yaml

from silicon_realms.engine import run


def test_simulation_runs():
    config = {
        "simulation": {"ticks": 10, "seed": 42, "log_interval": 5},
        "realms": {
            "compute": {"capacity": 50, "base_reward": 10, "difficulty_growth": 0.02},
            "memory": {"capacity": 40, "base_reward": 8, "decay_rate": 0.01},
            "network": {"capacity": 30, "base_reward": 12, "routing_fee": 0.05},
        },
        "economy": {
            "initial_supply": 1000,
            "mint_rate": 50,
            "stake_min": 10,
            "stake_reward_rate": 0.03,
            "transfer_fee": 0.01,
        },
        "agents": {"initial_count": 9},
    }

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        path = f.name

    try:
        state = run(path, plot=False)
        assert state.tick == 9  # 0-indexed, last tick is 9
        assert len(state.agents) == 9
        assert state.total_supply > 0
        assert len(state.ledger.transactions) > 0

        # Verify supply consistency: total_supply should equal sum of balances + staked
        agent_total = sum(a.balance + a.staked for a in state.agents.values())
        assert abs(state.total_supply - agent_total) < 0.01, \
            f"Supply mismatch: {state.total_supply} vs {agent_total}"
    finally:
        os.unlink(path)
