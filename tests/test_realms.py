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


def test_agent_spawn_tracking():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
    agent = AgentState(
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="test"),
        budget=100.0,
    )
    rm.on_agent_spawn(agent)
    assert agent.realm == Realm.RESEARCH
    assert rm.realms[Realm.RESEARCH].agents_active == 1
    mem.close()


def test_freeze_thaw():
    mem = Memory(":memory:")
    rm = RealmManager(mem)
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
