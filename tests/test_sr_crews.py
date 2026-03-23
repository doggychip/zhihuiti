"""Tests for the CrewAI economy tools (no API key needed)."""

from silicon_realms.crews.tools import (
    check_balance,
    transfer_tokens,
    stake_tokens,
    view_economy_summary,
    award_tokens,
    reset_economy,
    get_economy,
)


def setup_function():
    reset_economy({"Alice": 100.0, "Bob": 50.0})


def test_check_balance():
    result = check_balance.run(agent_name="Alice")
    assert "100.0" in result
    assert "Alice" in result


def test_transfer_tokens():
    result = transfer_tokens.run(sender="Alice", receiver="Bob", amount=10.0)
    assert "Transferred" in result
    econ = get_economy()
    assert econ["balances"]["Alice"] < 100.0  # paid 10 + fee
    assert econ["balances"]["Bob"] == 60.0


def test_transfer_insufficient():
    result = transfer_tokens.run(sender="Bob", receiver="Alice", amount=999.0)
    assert "failed" in result


def test_stake_tokens():
    result = stake_tokens.run(agent_name="Alice", amount=20.0)
    assert "staked" in result
    econ = get_economy()
    assert econ["staked"]["Alice"] == 20.0
    assert econ["balances"]["Alice"] == 80.0


def test_stake_minimum():
    result = stake_tokens.run(agent_name="Alice", amount=5.0)
    assert "minimum" in result


def test_award_tokens():
    result = award_tokens.run(agent_name="Bob", amount=25.0, reason="good work")
    assert "Awarded" in result
    econ = get_economy()
    assert econ["balances"]["Bob"] == 75.0


def test_view_economy_summary():
    result = view_economy_summary.run()
    assert "Alice" in result
    assert "Bob" in result
    assert "Total supply" in result
