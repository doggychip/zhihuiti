"""Tests for token economy system."""

from zhihuiti.economy import (
    CentralBank, Economy, RewardEngine, TaxBureau, Treasury,
    INITIAL_MONEY_SUPPLY, TAX_RATE,
)
from zhihuiti.memory import Memory


def test_central_bank_genesis():
    mem = Memory(":memory:")
    cb = CentralBank(mem)
    cb.genesis()
    assert cb.total_minted == INITIAL_MONEY_SUPPLY
    assert cb.money_supply == INITIAL_MONEY_SUPPLY
    mem.close()


def test_central_bank_mint_burn():
    mem = Memory(":memory:")
    cb = CentralBank(mem)
    cb.mint(100.0, "test", "test mint")
    assert cb.total_minted == 100.0
    cb.burn(30.0, "test", "test burn")
    assert cb.total_burned == 30.0
    assert cb.money_supply == 70.0
    mem.close()


def test_treasury_fund():
    mem = Memory(":memory:")
    t = Treasury(mem)
    t.balance = 500.0
    assert t.fund_agent_spawn(100.0) is True
    assert t.balance == 400.0
    assert t.fund_agent_spawn(500.0) is False
    mem.close()


def test_tax_bureau():
    mem = Memory(":memory:")
    t = Treasury(mem)
    t.balance = 0.0
    tb = TaxBureau(t, mem)
    net, tax = tb.tax_earning(100.0, "agent1")
    assert abs(tax - 100.0 * TAX_RATE) < 0.01
    assert abs(net - 100.0 * (1 - TAX_RATE)) < 0.01
    assert t.balance == tax
    mem.close()


def test_reward_engine():
    mem = Memory(":memory:")
    cb = CentralBank(mem)
    cb.genesis()
    t = Treasury(mem)
    t.balance = INITIAL_MONEY_SUPPLY
    tb = TaxBureau(t, mem)
    re = RewardEngine(cb, t, tb, mem)

    reward = re.calculate_reward(0.0)
    assert reward == 0.0

    reward = re.calculate_reward(1.0)
    assert reward > 0

    reward_low = re.calculate_reward(0.3)
    reward_high = re.calculate_reward(0.9)
    assert reward_high > reward_low
    mem.close()


def test_economy_full_cycle():
    mem = Memory(":memory:")
    econ = Economy(mem)

    # Fund spawn
    assert econ.fund_spawn(100.0) is True

    # Reward agent
    budget_ref = [50.0]
    result = econ.reward_agent("agent1", 0.8, budget_ref)
    assert result["paid"] is True
    assert result["net"] > 0
    assert budget_ref[0] > 50.0  # Budget increased

    # Burn
    econ.burn_agent_balance("agent1", 10.0)

    report = econ.get_report()
    assert report["total_minted"] > 0
    assert report["total_burned"] > 0
    mem.close()
