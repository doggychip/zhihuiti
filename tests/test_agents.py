"""Tests for AgentManager and _parse_delegation."""

from __future__ import annotations

import json
import pytest

from zhihuiti.agents import AgentManager, MAX_DEPTH, TASK_COST, _parse_delegation
from zhihuiti.economy import Economy
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState, Task, TaskStatus
from tests.conftest import make_stub_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup() -> tuple[AgentManager, Memory]:
    mem = Memory(":memory:")
    econ = Economy(mem)
    mgr = AgentManager(llm=make_stub_llm("task output"), memory=mem, economy=econ)
    return mgr, mem


def _spawn(mgr: AgentManager, role: AgentRole = AgentRole.RESEARCHER,
           budget: float = 100.0) -> AgentState:
    return mgr.spawn(role=role, depth=0, budget=budget)


# ---------------------------------------------------------------------------
# _parse_delegation
# ---------------------------------------------------------------------------

class TestParseDelegation:
    def test_returns_none_for_plain_text(self):
        assert _parse_delegation("Here is my answer to the question.") is None

    def test_returns_none_for_invalid_json(self):
        assert _parse_delegation("{not valid json}") is None

    def test_returns_none_for_json_without_action(self):
        assert _parse_delegation('{"key": "value"}') is None

    def test_returns_none_for_wrong_action(self):
        data = json.dumps({"action": "respond", "subtasks": [{"description": "t"}]})
        assert _parse_delegation(data) is None

    def test_returns_none_for_empty_subtasks(self):
        data = json.dumps({"action": "delegate", "subtasks": []})
        assert _parse_delegation(data) is None

    def test_returns_subtasks_for_valid_delegation(self):
        data = json.dumps({
            "action": "delegate",
            "subtasks": [
                {"description": "Research A", "role": "researcher"},
                {"description": "Analyze B", "role": "analyst"},
            ],
        })
        result = _parse_delegation(data)
        assert result is not None
        assert len(result) == 2
        assert result[0]["description"] == "Research A"

    def test_strips_markdown_fences(self):
        inner = json.dumps({
            "action": "delegate",
            "subtasks": [{"description": "task"}],
        })
        fenced = f"```\n{inner}\n```"
        result = _parse_delegation(fenced)
        assert result is not None
        assert len(result) == 1

    def test_returns_none_for_list_json(self):
        assert _parse_delegation('[{"description": "t"}]') is None


# ---------------------------------------------------------------------------
# AgentManager.spawn
# ---------------------------------------------------------------------------

class TestSpawn:
    def test_spawn_returns_agent(self):
        mgr, _ = _setup()
        agent = _spawn(mgr)
        assert agent.alive is True
        assert agent.config.role == AgentRole.RESEARCHER

    def test_spawn_adds_to_agents_dict(self):
        mgr, _ = _setup()
        agent = _spawn(mgr)
        assert agent.id in mgr.agents

    def test_spawn_saves_to_db(self):
        mgr, mem = _setup()
        agent = _spawn(mgr)
        row = mem.conn.execute(
            "SELECT id, alive FROM agents WHERE id = ?", (agent.id,)
        ).fetchone()
        assert row is not None
        assert row["alive"] == 1

    def test_spawn_deducts_from_treasury(self):
        mem = Memory(":memory:")
        econ = Economy(mem)
        initial_balance = econ.treasury.balance
        mgr = AgentManager(llm=make_stub_llm(), memory=mem, economy=econ)
        _spawn(mgr, budget=100.0)
        assert econ.treasury.balance < initial_balance

    def test_spawn_respects_budget(self):
        mgr, _ = _setup()
        agent = _spawn(mgr, budget=42.0)
        assert agent.budget == pytest.approx(42.0)

    def test_spawn_raises_beyond_max_depth(self):
        mgr, _ = _setup()
        with pytest.raises(ValueError, match="depth"):
            mgr.spawn(role=AgentRole.RESEARCHER, depth=MAX_DEPTH + 1, budget=100.0)

    def test_spawn_at_max_depth_is_ok(self):
        mgr, _ = _setup()
        agent = mgr.spawn(role=AgentRole.RESEARCHER, depth=MAX_DEPTH, budget=100.0)
        assert agent.depth == MAX_DEPTH

    def test_spawn_uses_provided_config(self):
        mgr, _ = _setup()
        config = AgentConfig(role=AgentRole.ANALYST, system_prompt="custom prompt")
        agent = mgr.spawn(role=AgentRole.ANALYST, config=config, budget=50.0)
        assert agent.config.system_prompt == "custom prompt"


# ---------------------------------------------------------------------------
# AgentManager.execute_task
# ---------------------------------------------------------------------------

class TestExecuteTask:
    def test_execute_returns_llm_output(self):
        mgr, _ = _setup()
        mgr.llm.chat.return_value = "Here is my research report."
        agent = _spawn(mgr)
        task = Task(description="Research topic X")
        result = mgr.execute_task(agent, task)
        assert "research" in result.lower()

    def test_execute_passes_model_to_llm(self):
        mgr, _ = _setup()
        mgr.llm.chat.return_value = "output"
        agent = _spawn(mgr)
        agent.config.model = "llama3.1"
        task = Task(description="task")
        mgr.execute_task(agent, task)
        _, kwargs = mgr.llm.chat.call_args
        assert kwargs.get("model") == "llama3.1"

    def test_execute_deducts_task_cost(self):
        mgr, _ = _setup()
        mgr.llm.chat.return_value = "done"
        agent = _spawn(mgr, budget=100.0)
        task = Task(description="task")
        mgr.execute_task(agent, task)
        assert agent.budget == pytest.approx(100.0 - TASK_COST)

    def test_execute_marks_task_completed(self):
        mgr, _ = _setup()
        mgr.llm.chat.return_value = "done"
        agent = _spawn(mgr)
        task = Task(description="task")
        mgr.execute_task(agent, task)
        assert task.status == TaskStatus.COMPLETED

    def test_execute_saves_task_to_db(self):
        mgr, mem = _setup()
        mgr.llm.chat.return_value = "output"
        agent = _spawn(mgr)
        task = Task(description="saved task")
        mgr.execute_task(agent, task)
        row = mem.conn.execute(
            "SELECT status FROM tasks WHERE id = ?", (task.id,)
        ).fetchone()
        assert row is not None
        assert row["status"] == "completed"

    def test_execute_fails_on_dead_agent(self):
        mgr, _ = _setup()
        agent = _spawn(mgr)
        agent.alive = False
        task = Task(description="task")
        with pytest.raises(ValueError, match="dead"):
            mgr.execute_task(agent, task)

    def test_execute_fails_gracefully_on_no_budget(self):
        mgr, _ = _setup()
        mgr.llm.chat.return_value = "done"
        agent = _spawn(mgr, budget=TASK_COST - 0.1)
        task = Task(description="task")
        result = mgr.execute_task(agent, task)
        assert task.status == TaskStatus.FAILED
        assert agent.alive is False
        assert "budget" in result.lower()

    def test_execute_handles_llm_error(self):
        mgr, _ = _setup()
        from zhihuiti.llm import LLMError
        mgr.llm.chat.side_effect = LLMError("connection refused")
        agent = _spawn(mgr)
        task = Task(description="task")
        result = mgr.execute_task(agent, task)
        assert task.status == TaskStatus.FAILED
        assert "Error" in result

    def test_execute_does_not_delegate_at_max_depth(self):
        mgr, _ = _setup()
        delegation_json = json.dumps({
            "action": "delegate",
            "subtasks": [{"description": "sub", "role": "researcher"}],
        })
        mgr.llm.chat.return_value = delegation_json
        # At max depth, delegation is ignored — must respond directly
        agent = mgr.spawn(role=AgentRole.RESEARCHER, depth=MAX_DEPTH, budget=100.0)
        task = Task(description="task at max depth")
        result = mgr.execute_task(agent, task)
        # Result is the raw delegation JSON (treated as direct response)
        assert task.status == TaskStatus.COMPLETED
        assert len(task.subtask_ids) == 0  # No sub-agents spawned

    def test_execute_delegates_when_valid_json(self):
        mgr, _ = _setup()
        delegation_json = json.dumps({
            "action": "delegate",
            "subtasks": [{"description": "do research", "role": "researcher"}],
        })
        # First call: delegation; subsequent calls: sub-task + synthesis
        mgr.llm.chat.side_effect = [
            delegation_json,       # parent returns delegation request
            "sub-task output",     # sub-agent direct response
            "synthesized output",  # parent synthesizes
        ]
        agent = mgr.spawn(role=AgentRole.RESEARCHER, depth=0, budget=200.0)
        task = Task(description="complex task")
        result = mgr.execute_task(agent, task)
        assert task.status == TaskStatus.COMPLETED
        assert len(task.subtask_ids) == 1
        assert "synthesized" in result or "sub-task" in result


# ---------------------------------------------------------------------------
# AgentManager.cull_agent
# ---------------------------------------------------------------------------

class TestCullAgent:
    def test_cull_marks_agent_dead(self):
        mgr, _ = _setup()
        agent = _spawn(mgr)
        mgr.cull_agent(agent)
        assert agent.alive is False

    def test_cull_sets_budget_zero(self):
        mgr, _ = _setup()
        agent = _spawn(mgr, budget=80.0)
        mgr.cull_agent(agent)
        assert agent.budget == pytest.approx(0.0)

    def test_cull_saves_dead_state_to_db(self):
        mgr, mem = _setup()
        agent = _spawn(mgr)
        mgr.cull_agent(agent)
        row = mem.conn.execute(
            "SELECT alive FROM agents WHERE id = ?", (agent.id,)
        ).fetchone()
        assert row["alive"] == 0

    def test_cull_burns_budget_in_economy(self):
        mem = Memory(":memory:")
        econ = Economy(mem)
        mgr = AgentManager(llm=make_stub_llm(), memory=mem, economy=econ)
        agent = _spawn(mgr, budget=50.0)
        burned_before = econ.central_bank.total_burned
        mgr.cull_agent(agent)
        assert econ.central_bank.total_burned > burned_before


# ---------------------------------------------------------------------------
# AgentManager.promote_to_gene_pool
# ---------------------------------------------------------------------------

class TestPromoteToGenePool:
    def test_promote_saves_to_gene_pool(self):
        mgr, mem = _setup()
        mgr.llm.premium_model = "llama3.1"
        agent = _spawn(mgr)
        agent.scores = [0.9, 0.85]
        mgr.promote_to_gene_pool(agent)
        rows = mem._query("SELECT * FROM gene_pool")
        assert len(rows) == 1

    def test_promote_stores_correct_score(self):
        mgr, mem = _setup()
        mgr.llm.premium_model = "llama3.1"
        agent = _spawn(mgr)
        agent.scores = [0.9]
        mgr.promote_to_gene_pool(agent)
        row = mem._query_one("SELECT avg_score FROM gene_pool")
        assert row["avg_score"] == pytest.approx(0.9)

    def test_promote_upgrades_model(self):
        mgr, mem = _setup()
        mgr.llm.premium_model = "llama3.1"
        agent = _spawn(mgr)
        agent.scores = [0.9]
        mgr.promote_to_gene_pool(agent)
        assert agent.config.model == "llama3.1"
        row = mem._query_one("SELECT model FROM gene_pool")
        assert row["model"] == "llama3.1"


# ---------------------------------------------------------------------------
# AgentManager.get_best_config
# ---------------------------------------------------------------------------

class TestGetBestConfig:
    def test_returns_none_when_no_genes(self):
        mgr, _ = _setup()
        config = mgr.get_best_config(AgentRole.RESEARCHER)
        assert config is None

    def test_returns_config_from_gene_pool(self):
        mgr, mem = _setup()
        mem.save_to_gene_pool(
            gene_id="gene-abc",
            role="researcher",
            system_prompt="you are a researcher",
            temperature=0.7,
            avg_score=0.85,
        )
        config = mgr.get_best_config(AgentRole.RESEARCHER)
        assert config is not None
        assert config.role == AgentRole.RESEARCHER

    def test_config_is_mutated_copy(self):
        mgr, mem = _setup()
        mem.save_to_gene_pool(
            gene_id="gene-xyz",
            role="analyst",
            system_prompt="analyst prompt",
            temperature=0.7,
            avg_score=0.8,
        )
        config = mgr.get_best_config(AgentRole.ANALYST)
        # Mutation sets a new gene_id and records parent
        assert config.parent_gene_id == "gene-xyz"

    def test_model_tier_inherited_from_gene_pool(self):
        mgr, mem = _setup()
        mem.save_to_gene_pool(
            gene_id="gene-premium",
            role="researcher",
            system_prompt="researcher prompt",
            temperature=0.7,
            avg_score=0.9,
            model="llama3.1",
        )
        config = mgr.get_best_config(AgentRole.RESEARCHER)
        assert config.model == "llama3.1"


# ---------------------------------------------------------------------------
# AgentManager.get_alive_agents
# ---------------------------------------------------------------------------

class TestGetAliveAgents:
    def test_returns_only_alive(self):
        mgr, _ = _setup()
        a1 = _spawn(mgr)
        a2 = _spawn(mgr)
        a2.alive = False
        alive = mgr.get_alive_agents()
        assert a1 in alive
        assert a2 not in alive

    def test_empty_when_all_culled(self):
        mgr, _ = _setup()
        agent = _spawn(mgr)
        mgr.cull_agent(agent)
        assert mgr.get_alive_agents() == []
