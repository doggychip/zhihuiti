"""Tests for Judge integration with the Adaptation Engine."""

from __future__ import annotations

import pytest

from zhihuiti.judge import Judge, DEFAULT_CULL_THRESHOLD, DEFAULT_PROMOTE_THRESHOLD
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState, Task, TaskStatus
from zhihuiti.economy import Economy
from zhihuiti.agents import AgentManager
from tests.conftest import make_stub_llm


def _setup() -> tuple[Judge, AgentManager, Memory]:
    mem = Memory(":memory:")
    econ = Economy(mem)
    llm = make_stub_llm()
    mgr = AgentManager(llm=llm, memory=mem, economy=econ)
    judge = Judge(llm=llm, memory=mem, agent_manager=mgr)
    return judge, mgr, mem


def _make_agent(mgr: AgentManager, role: AgentRole = AgentRole.RESEARCHER,
                budget: float = 100.0) -> AgentState:
    return mgr.spawn(role=role, depth=0, budget=budget)


def _make_task(result: str = "Some output", status: TaskStatus = TaskStatus.COMPLETED) -> Task:
    task = Task(description="Test task")
    task.result = result
    task.status = status
    return task


# ═══════════════════════════════════════════════════════════════════════════════
# Judge basic functionality (preserved from original)
# ═══════════════════════════════════════════════════════════════════════════════

class TestJudgeScoring:
    def test_score_task_returns_float(self):
        judge, mgr, mem = _setup()
        agent = _make_agent(mgr)
        task = _make_task()
        score = judge.score_task(task, agent)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        mem.close()

    def test_score_task_appends_to_agent_scores(self):
        judge, mgr, mem = _setup()
        agent = _make_agent(mgr)
        task = _make_task()
        judge.score_task(task, agent)
        assert len(agent.scores) == 1
        mem.close()

    def test_score_task_sets_task_score(self):
        judge, mgr, mem = _setup()
        agent = _make_agent(mgr)
        task = _make_task()
        judge.score_task(task, agent)
        assert task.score is not None
        mem.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Adaptive thresholds integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdaptiveThresholdsIntegration:
    def test_initial_thresholds_are_defaults(self):
        judge, _, mem = _setup()
        assert judge.cull_threshold == DEFAULT_CULL_THRESHOLD
        assert judge.promote_threshold == DEFAULT_PROMOTE_THRESHOLD
        mem.close()

    def test_thresholds_adapt_after_evaluation_cycle(self):
        judge, mgr, mem = _setup()
        mgr.llm.premium_model = "llama3.1"
        # Create agents with varying scores
        agents = []
        for i in range(10):
            agent = _make_agent(mgr)
            agent.scores = [0.3 + i * 0.06]  # 0.3 to 0.84
            agents.append(agent)

        result = judge.run_evaluation_cycle(agents)
        assert "cull_threshold" in result
        assert "promote_threshold" in result
        mem.close()

    def test_evaluation_cycle_returns_alive_count(self):
        judge, mgr, mem = _setup()
        agents = [_make_agent(mgr) for _ in range(5)]
        for a in agents:
            a.scores = [0.5]
        result = judge.run_evaluation_cycle(agents)
        assert result["alive"] >= 0
        mem.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Performance tracker integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceTrackerIntegration:
    def test_score_task_feeds_tracker(self):
        judge, mgr, mem = _setup()
        agent = _make_agent(mgr)
        task = _make_task()
        judge.score_task(task, agent)

        role = agent.config.role.value
        summary = judge.performance_tracker.get_role_summary(role)
        assert summary is not None
        assert summary["total_scores"] == 1
        mem.close()

    def test_multiple_scores_tracked(self):
        judge, mgr, mem = _setup()
        for _ in range(5):
            agent = _make_agent(mgr)
            task = _make_task()
            judge.score_task(task, agent)

        role = "researcher"
        summary = judge.performance_tracker.get_role_summary(role)
        assert summary["total_scores"] == 5
        mem.close()

    def test_get_mutation_rate(self):
        judge, mgr, mem = _setup()
        # Record some scores
        for _ in range(5):
            agent = _make_agent(mgr)
            task = _make_task()
            judge.score_task(task, agent)

        rate = judge.get_mutation_rate("researcher")
        assert 0.0 < rate < 1.0
        mem.close()

    def test_mutation_rate_default_for_unknown_role(self):
        judge, _, mem = _setup()
        rate = judge.get_mutation_rate("nonexistent_role")
        assert rate == 0.15
        mem.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt evolution integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestPromptEvolverIntegration:
    def test_score_task_feeds_evolver(self):
        judge, mgr, mem = _setup()
        for _ in range(5):
            agent = _make_agent(mgr)
            task = _make_task()
            judge.score_task(task, agent)

        report = judge.prompt_evolver.get_role_report()
        assert "researcher" in report
        mem.close()

    def test_get_evolved_prompt(self):
        judge, mgr, mem = _setup()
        # Create some failure patterns
        # Simulate by recording directly into the evolver
        for _ in range(10):
            judge.prompt_evolver.record_inspection(
                "researcher",
                {"rigor": 0.2, "relevance": 0.8},
                {"rigor": 0.5, "relevance": 0.4},
            )

        base = "You are a researcher."
        evolved = judge.get_evolved_prompt(base, "researcher")
        assert len(evolved) > len(base)
        assert "Performance Improvement" in evolved
        mem.close()

    def test_no_evolution_without_failures(self):
        judge, _, mem = _setup()
        base = "You are a researcher."
        evolved = judge.get_evolved_prompt(base, "researcher")
        assert evolved == base  # No data → no change
        mem.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Evaluate agent with adaptive thresholds
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluateAgent:
    def test_cull_below_threshold(self):
        judge, mgr, mem = _setup()
        agent = _make_agent(mgr)
        agent.scores = [0.1, 0.15, 0.2]  # Below default cull of 0.3
        judge.evaluate_agent(agent)
        assert agent.alive is False
        mem.close()

    def test_promote_above_threshold(self):
        judge, mgr, mem = _setup()
        mgr.llm.premium_model = "llama3.1"
        agent = _make_agent(mgr)
        agent.scores = [0.85, 0.9]  # Above default promote of 0.8
        judge.evaluate_agent(agent)
        # Agent should still be alive (promoted, not culled)
        assert agent.alive is True
        mem.close()

    def test_no_action_in_middle(self):
        judge, mgr, mem = _setup()
        agent = _make_agent(mgr)
        agent.scores = [0.5]  # Between cull and promote
        judge.evaluate_agent(agent)
        assert agent.alive is True
        mem.close()

    def test_no_action_without_scores(self):
        judge, mgr, mem = _setup()
        agent = _make_agent(mgr)
        judge.evaluate_agent(agent)
        assert agent.alive is True
        mem.close()
