import random
from silicon_realms.models import Agent, Ledger, Realm, SimState
from silicon_realms.economy import mint, transfer, stake, unstake, distribute_staking_rewards, get_summary


def make_state():
    state = SimState(
        rng=random.Random(42),
        config={"economy": {"transfer_fee": 0.01, "stake_min": 10, "stake_reward_rate": 0.03}},
    )
    state.realms["compute"] = Realm("compute", 50, 10)
    state.agents["a1"] = Agent(id="a1", name="Alpha", realm="compute", balance=100.0)
    state.agents["a2"] = Agent(id="a2", name="Beta", realm="compute", balance=50.0)
    return state


def test_mint():
    state = make_state()
    mint(state, "a1", 25.0)
    assert state.agents["a1"].balance == 125.0
    assert state.total_supply == 25.0
    assert len(state.ledger.transactions) == 1
    assert state.ledger.transactions[0].tx_type == "mint"


def test_transfer():
    state = make_state()
    state.total_supply = 150.0
    ok = transfer(state, "a1", "a2", 10.0)
    assert ok
    assert state.agents["a1"].balance < 90.0  # 100 - 10 - fee
    assert state.agents["a2"].balance == 60.0
    assert state.total_supply < 150.0  # fee burned


def test_transfer_insufficient():
    state = make_state()
    ok = transfer(state, "a2", "a1", 1000.0)
    assert not ok
    assert state.agents["a2"].balance == 50.0


def test_stake_and_unstake():
    state = make_state()
    ok = stake(state, "a1", 30.0)
    assert ok
    assert state.agents["a1"].balance == 70.0
    assert state.agents["a1"].staked == 30.0

    ok = unstake(state, "a1", 15.0)
    assert ok
    assert state.agents["a1"].balance == 85.0
    assert state.agents["a1"].staked == 15.0


def test_stake_minimum():
    state = make_state()
    ok = stake(state, "a1", 5.0)  # below minimum of 10
    assert not ok
    assert state.agents["a1"].balance == 100.0


def test_staking_rewards():
    state = make_state()
    state.agents["a1"].staked = 100.0
    distribute_staking_rewards(state)
    assert state.agents["a1"].balance == 100.0 + 100.0 * 0.03
    assert state.total_supply == 100.0 * 0.03


def test_summary():
    state = make_state()
    state.total_supply = 150.0
    summary = get_summary(state)
    assert summary["total_supply"] == 150.0
    assert "compute" in summary["realm_population"]
