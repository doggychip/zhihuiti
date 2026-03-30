"""Tests for relationship graph and lending system."""

from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState
from zhihuiti.relationships import LendingSystem, RelationshipGraph, RelationType


def _make_agent(agent_id: str, budget: float = 100.0, score: float = 0.7) -> AgentState:
    a = AgentState(
        id=agent_id,
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="test"),
        budget=budget,
    )
    a.scores = [score]
    return a


def test_add_relationship():
    mem = Memory(":memory:")
    graph = RelationshipGraph(mem)
    rel_id = graph.add(RelationType.TRANSACTION, "a1", "a2")
    assert rel_id
    rels = graph.get_agent_relations("a1")
    assert len(rels) == 1
    mem.close()


def test_connected_agents():
    mem = Memory(":memory:")
    graph = RelationshipGraph(mem)
    graph.add(RelationType.TRANSACTION, "a1", "a2")
    graph.add(RelationType.COMPETITION, "a1", "a3")
    connected = graph.get_connected_agents("a1")
    assert "a2" in connected
    assert "a3" in connected
    assert "a1" not in connected
    mem.close()


def test_strengthen():
    mem = Memory(":memory:")
    graph = RelationshipGraph(mem)
    rel_id = graph.add(RelationType.TRANSACTION, "a1", "a2", strength=1.0)
    graph.strengthen(rel_id, delta=0.5)
    rels = graph.get_agent_relations("a1")
    assert rels[0]["strength"] == 1.5
    mem.close()


def test_loan_request():
    mem = Memory(":memory:")
    graph = RelationshipGraph(mem)
    lending = LendingSystem(mem, graph)

    lender = _make_agent("lender", budget=200.0, score=0.8)
    borrower = _make_agent("borrower", budget=10.0, score=0.6)
    agents = {a.id: a for a in [lender, borrower]}

    loan = lending.request_loan(borrower, agents, amount=30.0)
    assert loan is not None
    assert loan.principal == 30.0
    assert borrower.budget == 40.0  # 10 + 30
    assert lender.budget == 170.0  # 200 - 30
    mem.close()


def test_auto_repay():
    mem = Memory(":memory:")
    graph = RelationshipGraph(mem)
    lending = LendingSystem(mem, graph)

    lender = _make_agent("lender", budget=200.0, score=0.8)
    borrower = _make_agent("borrower", budget=10.0, score=0.6)
    agents = {a.id: a for a in [lender, borrower]}

    loan = lending.request_loan(borrower, agents, amount=30.0)
    repaid = lending.auto_repay(borrower, reward_amount=20.0)
    assert repaid > 0
    assert repaid == 6.0  # 30% of 20
    mem.close()


def test_default_loans():
    mem = Memory(":memory:")
    graph = RelationshipGraph(mem)
    lending = LendingSystem(mem, graph)

    lender = _make_agent("lender", budget=200.0, score=0.8)
    borrower = _make_agent("borrower", budget=10.0, score=0.6)
    agents = {a.id: a for a in [lender, borrower]}

    lending.request_loan(borrower, agents, amount=30.0)
    borrower.alive = False
    defaulted = lending.default_loans(borrower)
    assert len(defaulted) == 1
    assert defaulted[0].status == "defaulted"
    mem.close()


def test_no_lender_found():
    mem = Memory(":memory:")
    graph = RelationshipGraph(mem)
    lending = LendingSystem(mem, graph)

    poor = _make_agent("poor", budget=5.0, score=0.3)
    agents = {poor.id: poor}

    loan = lending.request_loan(poor, agents, amount=50.0)
    assert loan is None
    mem.close()


def test_stats():
    mem = Memory(":memory:")
    graph = RelationshipGraph(mem)
    graph.add(RelationType.TRANSACTION, "a1", "a2")
    graph.add(RelationType.BLOODLINE, "a1", "a3")

    stats = graph.get_stats()
    assert stats["total_relationships"] == 2
    assert stats["agents_connected"] == 3
    assert stats["by_type"]["transaction"] == 1
    assert stats["by_type"]["bloodline"] == 1
    mem.close()
