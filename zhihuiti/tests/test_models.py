"""Tests for core models."""

from zhihuiti.models import (
    AgentConfig, AgentRole, AgentLifeState, AgentState,
    Realm, ROLE_TO_REALM, Task, TaskStatus,
)


def test_agent_config_mutate():
    config = AgentConfig(
        role=AgentRole.RESEARCHER,
        system_prompt="test prompt",
        temperature=0.7,
        gene_id="gene_001",
    )
    mutated = config.mutate("test mutation")
    assert mutated.gene_id != config.gene_id
    assert mutated.parent_gene_id == "gene_001"
    assert mutated.role == AgentRole.RESEARCHER
    assert 0.1 <= mutated.temperature <= 1.0


def test_agent_state_avg_score():
    agent = AgentState()
    assert agent.avg_score == 0.5  # Default with no scores
    agent.scores = [0.6, 0.8, 1.0]
    assert abs(agent.avg_score - 0.8) < 0.001


def test_agent_state_deduct_budget():
    agent = AgentState(budget=50.0)
    assert agent.deduct_budget(30.0) is True
    assert agent.budget == 20.0
    assert agent.deduct_budget(30.0) is False
    assert agent.budget == 20.0


def test_task_is_terminal():
    task = Task(status=TaskStatus.PENDING)
    assert not task.is_terminal
    task.status = TaskStatus.COMPLETED
    assert task.is_terminal
    task.status = TaskStatus.FAILED
    assert task.is_terminal


def test_realm_mapping():
    assert ROLE_TO_REALM[AgentRole.RESEARCHER] == Realm.RESEARCH
    assert ROLE_TO_REALM[AgentRole.CODER] == Realm.RESEARCH
    assert ROLE_TO_REALM[AgentRole.TRADER] == Realm.EXECUTION
    assert ROLE_TO_REALM[AgentRole.JUDGE] == Realm.CENTRAL
    assert ROLE_TO_REALM[AgentRole.ORCHESTRATOR] == Realm.CENTRAL


def test_agent_state_realm_default():
    agent = AgentState()
    assert agent.realm == Realm.EXECUTION
    assert agent.life_state == AgentLifeState.ACTIVE
