"""Tests for three realms system."""

from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentLifeState, AgentRole, AgentState, Realm
from zhihuiti.realms import RealmManager


def test_realm_assignment():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    assert rm.assign_realm(AgentRole.RESEARCHER) == Realm.RESEARCH
    assert rm.assign_realm(AgentRole.CODER) == Realm.RESEARCH
    assert rm.assign_realm(AgentRole.TRADER) == Realm.EXECUTION
    assert rm.assign_realm(AgentRole.JUDGE) == Realm.CENTRAL
    mem.close()


def test_budget_allocation():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(1000.0)
    assert rm.realms[Realm.RESEARCH].budget_allocated == 500.0
    assert rm.realms[Realm.EXECUTION].budget_allocated == 350.0
    assert rm.realms[Realm.CENTRAL].budget_allocated == 150.0
    mem.close()


def test_reset_budget_starts_a_fresh_runtime_window():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(1000.0)
    rm.realms[Realm.RESEARCH].budget_spent = 400.0
    rm.allocate_budgets(1000.0, reset=True)

    assert rm.realms[Realm.RESEARCH].budget_allocated == 500.0
    assert rm.realms[Realm.RESEARCH].budget_spent == 0.0
    assert rm.realms[Realm.RESEARCH].budget_remaining == 500.0
    mem.close()


def test_spawn_rejects_realm_budget_overrun():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(100.0, reset=True)
    agent = AgentState(
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="test"),
        budget=60.0,
    )

    import pytest
    with pytest.raises(ValueError, match="budget exhausted"):
        rm.on_agent_spawn(agent)
    mem.close()


def test_agent_spawn_tracking():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(200.0, reset=True)
    agent = AgentState(
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="test"),
        budget=100.0,
    )
    rm.on_agent_spawn(agent)
    assert agent.realm == Realm.RESEARCH
    assert rm.realms[Realm.RESEARCH].agents_active == 1
    mem.close()


def test_scheduled_quota_replenishment_requires_treasury_backing():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(100.0, reset=True)
    research = rm.realms[Realm.RESEARCH]
    research.budget_spent = research.budget_allocated

    import pytest
    with pytest.raises(ValueError, match="Treasury cannot back"):
        rm.replenish_spawn_quota(
            AgentRole.RESEARCHER, 25.0, treasury_available=24.9,
        )

    added = rm.replenish_spawn_quota(
        AgentRole.RESEARCHER, 25.0, treasury_available=25.0,
    )
    assert added == 25.0
    assert research.budget_remaining == 25.0
    mem.close()


def test_scheduled_quota_replenishment_rejects_invalid_amounts():
    mem = Memory(":memory:")
    rm = RealmManager(mem)

    import pytest
    for invalid in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="positive finite"):
            rm.replenish_spawn_quota(
                AgentRole.RESEARCHER, invalid, treasury_available=100.0,
            )
    mem.close()


def test_cull_releases_unused_quota_without_refunding_tokens():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(200.0, reset=True)
    agent = AgentState(
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="test"),
        budget=40.0,
    )
    rm.on_agent_spawn(agent)

    agent.budget = 0.0
    rm.on_agent_cull(agent, unused_budget=35.0, quota_release=35.0)

    state = rm.realms[Realm.RESEARCH]
    assert state.budget_spent == 5.0
    assert state.budget_remaining == 95.0
    assert agent.life_state == AgentLifeState.FROZEN
    mem.close()


def test_rewarded_balance_cannot_over_release_original_quota():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(200.0, reset=True)
    agent = AgentState(
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="test"),
        budget=75.0,
    )
    rm.on_agent_spawn(agent)

    agent.budget = 0.0
    rm.on_agent_cull(agent, unused_budget=75.0, quota_release=40.0)

    state = rm.realms[Realm.RESEARCH]
    assert state.budget_spent == 35.0
    assert state.budget_remaining == 65.0
    mem.close()


def test_freeze_thaw():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(200.0, reset=True)
    agent = AgentState(
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="test"),
        budget=100.0,
    )
    rm.on_agent_spawn(agent)

    rm.freeze_agent(agent)
    assert agent.life_state == AgentLifeState.FROZEN
    assert not agent.alive
    assert rm.realms[Realm.RESEARCH].agents_frozen == 1

    rm.thaw_agent(agent)
    assert agent.life_state == AgentLifeState.ACTIVE
    assert agent.alive
    assert rm.realms[Realm.RESEARCH].agents_frozen == 0
    mem.close()


def test_bankrupt():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(2.0, reset=True)
    agent = AgentState(
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="test"),
        budget=0.5,
    )
    rm.on_agent_spawn(agent)
    rm.on_agent_cull(agent)
    assert agent.life_state == AgentLifeState.BANKRUPT
    mem.close()


def test_persistence():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    rm.allocate_budgets(1000.0)

    rm2 = RealmManager(mem)
    assert rm2.realms[Realm.RESEARCH].budget_allocated == 500.0
    mem.close()
