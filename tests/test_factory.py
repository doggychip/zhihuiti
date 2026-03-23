"""Tests for the Factory (血汗工厂) module."""

from __future__ import annotations

import pytest

from zhihuiti.factory import (
    Factory, ProductionOrder, ProductionStatus,
    BASE_REVENUE_PER_SUBTASK, QA_THRESHOLD, MAX_REWORK_CYCLES, WORKER_SHARE,
)
from zhihuiti.models import AgentState, AgentConfig, AgentRole
from zhihuiti.memory import Memory
from tests.conftest import make_stub_llm


def _make_memory() -> Memory:
    return Memory(":memory:")


def _make_agent(budget: float = 100.0) -> AgentState:
    return AgentState(
        config=AgentConfig(role=AgentRole.CODER, system_prompt=""),
        budget=budget,
    )


def _make_factory() -> Factory:
    mem = _make_memory()
    llm = make_stub_llm({"score": 0.8, "reasoning": "good quality output", "pass": True})
    return Factory(llm=llm, memory=mem)


# ---------------------------------------------------------------------------
# ProductionOrder data model
# ---------------------------------------------------------------------------

class TestProductionOrder:
    def test_is_complete_when_all_results_in(self):
        order = ProductionOrder(
            subtasks=["task1", "task2"],
            results={"id_sub0": "done1", "id_sub1": "done2"},
        )
        assert order.is_complete is True

    def test_not_complete_when_missing_results(self):
        order = ProductionOrder(subtasks=["task1", "task2"])
        assert order.is_complete is False

    def test_to_dict(self):
        order = ProductionOrder(description="Test order", subtasks=["t1"])
        d = order.to_dict()
        assert d["description"] == "Test order"
        assert d["status"] == ProductionStatus.QUEUED.value
        assert "subtasks" in d

    def test_initial_status_queued(self):
        order = ProductionOrder()
        assert order.status == ProductionStatus.QUEUED

    def test_rework_count_starts_at_zero(self):
        order = ProductionOrder()
        assert order.rework_count == 0


# ---------------------------------------------------------------------------
# create_order with explicit subtasks
# ---------------------------------------------------------------------------

class TestCreateOrder:
    def test_create_order_with_subtasks(self):
        factory = _make_factory()
        order = factory.create_order(
            "Build a market report",
            subtasks=["Research", "Draft", "Validate"]
        )
        assert order.description == "Build a market report"
        assert len(order.subtasks) == 3
        assert order.id in factory.orders

    def test_revenue_calculated_from_subtasks(self):
        factory = _make_factory()
        order = factory.create_order("test", subtasks=["a", "b", "c"])
        assert order.revenue == pytest.approx(3 * BASE_REVENUE_PER_SUBTASK)

    def test_single_subtask_revenue(self):
        factory = _make_factory()
        order = factory.create_order("test", subtasks=["only task"])
        assert order.revenue == pytest.approx(BASE_REVENUE_PER_SUBTASK)

    def test_order_tracked_in_factory(self):
        factory = _make_factory()
        order1 = factory.create_order("order1", subtasks=["t1"])
        order2 = factory.create_order("order2", subtasks=["t2"])
        assert len(factory.orders) == 2
        assert order1.id in factory.orders
        assert order2.id in factory.orders


# ---------------------------------------------------------------------------
# assign_workers
# ---------------------------------------------------------------------------

class TestAssignWorkers:
    def test_assign_workers_round_robin(self):
        factory = _make_factory()
        order = factory.create_order("task", subtasks=["a", "b", "c", "d"])
        agents = [_make_agent(), _make_agent()]

        assignments = factory.assign_workers(order, agents)

        # 4 subtasks, 2 agents → round-robin assignment
        assert len(assignments) == 4
        agent_ids = set(assignments.values())
        assert len(agent_ids) == 2  # Both agents used

    def test_assign_workers_sets_in_progress(self):
        factory = _make_factory()
        order = factory.create_order("task", subtasks=["a", "b"])
        agents = [_make_agent()]

        factory.assign_workers(order, agents)
        assert order.status == ProductionStatus.IN_PROGRESS

    def test_assign_workers_empty_agents(self):
        factory = _make_factory()
        order = factory.create_order("task", subtasks=["a"])
        result = factory.assign_workers(order, [])
        assert result == {}


# ---------------------------------------------------------------------------
# process_order
# ---------------------------------------------------------------------------

class TestProcessOrder:
    def test_process_order_uses_execute_fn(self):
        factory = _make_factory()
        order = factory.create_order("task", subtasks=["subtask_1", "subtask_2"])
        agent = _make_agent()
        factory.assign_workers(order, [agent])

        executed = []

        def execute_fn(ag, desc):
            executed.append(desc)
            return f"result: {desc}"

        agents_dict = {agent.id: agent}
        factory.process_order(order, agents_dict, execute_fn=execute_fn)

        assert len(executed) == 2
        assert len(order.results) == 2

    def test_process_order_placeholder_when_no_fn(self):
        factory = _make_factory()
        order = factory.create_order("task", subtasks=["a", "b"])
        agent = _make_agent()
        factory.assign_workers(order, [agent])

        factory.process_order(order, {agent.id: agent}, execute_fn=None)

        # Placeholder results should be set
        assert len(order.results) == 2
        for result in order.results.values():
            assert "placeholder" in result.lower() or result  # non-empty

    def test_process_order_marks_complete(self):
        factory = _make_factory()
        order = factory.create_order("task", subtasks=["a"])
        agent = _make_agent()
        factory.assign_workers(order, [agent])

        factory.process_order(order, {agent.id: agent})
        assert order.is_complete


# ---------------------------------------------------------------------------
# ship / revenue distribution
# ---------------------------------------------------------------------------

class TestShipOrder:
    def test_ship_sets_shipped_status(self):
        factory = _make_factory()
        order = factory.create_order("task", subtasks=["a", "b"])
        agent = _make_agent()
        factory.assign_workers(order, [agent])
        factory.process_order(order, {agent.id: agent})
        order.status = ProductionStatus.QA_PASS  # force pass

        factory.ship(order)
        assert order.status == ProductionStatus.SHIPPED

    def test_ship_increments_total_shipped(self):
        factory = _make_factory()
        order = factory.create_order("task", subtasks=["a"])
        agent = _make_agent()
        factory.assign_workers(order, [agent])
        factory.process_order(order, {agent.id: agent})
        order.status = ProductionStatus.QA_PASS

        factory.ship(order)
        assert factory.total_shipped == 1

    def test_ship_returns_payouts(self):
        factory = _make_factory()
        order = factory.create_order("task", subtasks=["a", "b"])
        agent = _make_agent(budget=0.0)
        factory.assign_workers(order, [agent])
        factory.process_order(order, {agent.id: agent})
        order.status = ProductionStatus.QA_PASS

        payouts = factory.ship(order)
        # Payouts dict should have agent's earnings
        assert agent.id in payouts
        assert payouts[agent.id] > 0.0


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestStats:
    def test_initial_stats(self):
        factory = _make_factory()
        assert factory.total_revenue == 0.0
        assert factory.total_shipped == 0
        assert factory.total_reworks == 0

    def test_get_stats(self):
        factory = _make_factory()
        factory.create_order("task1", subtasks=["a"])
        factory.create_order("task2", subtasks=["b", "c"])

        stats = factory.get_stats()
        assert stats["total_orders"] == 2
        assert stats["shipped"] == 0
