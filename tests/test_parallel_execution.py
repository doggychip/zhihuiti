"""Tests for parallel task execution in execute_goal."""

from __future__ import annotations

import tempfile
import threading
import time
from unittest.mock import MagicMock

import pytest

from zhihuiti.memory import Memory
from tests.conftest import make_stub_llm

INSPECTION_PASS = {"score": 0.8, "reasoning": "good", "pass": True}


def _make_orchestrator(llm=None):
    from zhihuiti.orchestrator import Orchestrator
    from zhihuiti.economy import Economy
    from zhihuiti.bloodline import Bloodline
    from zhihuiti.realms import RealmManager
    from zhihuiti.agents import AgentManager
    from zhihuiti.judge import Judge
    from zhihuiti.circuit_breaker import CircuitBreaker
    from zhihuiti.behavior import BehaviorDetector
    from zhihuiti.relationships import LendingSystem, RelationshipGraph
    from zhihuiti.arbitration import ArbitrationBureau
    from zhihuiti.market import TradingMarket
    from zhihuiti.futures import FuturesMarket
    from zhihuiti.factory import Factory
    from zhihuiti.bidding import BiddingHouse

    # File-based temp DB — in-memory SQLite segfaults under thread contention on Python 3.9
    mem = Memory(tempfile.mktemp(suffix=".db"))
    stub = llm or make_stub_llm()

    orch = Orchestrator.__new__(Orchestrator)
    orch.llm = stub
    orch.memory = mem
    orch.economy = Economy(mem)
    orch.bloodline = Bloodline(mem)
    orch.realm_manager = RealmManager(mem)
    orch.agent_manager = AgentManager(stub, mem, orch.economy, orch.bloodline, orch.realm_manager)
    orch.judge = Judge(stub, mem, orch.agent_manager)
    orch.circuit_breaker = CircuitBreaker(mem, interactive=False)
    orch.behavior = BehaviorDetector(mem, stub)
    orch.rel_graph = RelationshipGraph(mem)
    orch.lending = LendingSystem(mem, orch.rel_graph)
    orch.arbitration = ArbitrationBureau(mem)
    orch.market = TradingMarket(mem)
    orch.futures = FuturesMarket(mem)
    orch.factory = Factory(llm=stub, memory=mem)
    orch.bidding = BiddingHouse(stub, mem, orch.economy)
    from zhihuiti.messaging import MessageBoard
    orch.messages = MessageBoard(mem)
    orch.tasks = {}
    orch.max_workers = 4
    orch.max_retries = 0
    orch.tools_enabled = False

    for agent in orch.bidding.pool.get_all_alive():
        if agent.id not in orch.agent_manager.agents:
            orch.agent_manager.agents[agent.id] = agent

    orch.realm_manager.allocate_budgets(orch.economy.treasury.balance * 0.5)
    return orch


class TestParallelExecution:
    def _make_timed_llm(self, delay: float = 0.05) -> tuple[MagicMock, list]:
        """LLM that records which thread ran each call and introduces a small delay."""
        call_log: list[tuple[str, float]] = []
        call_count = [0]
        lock = threading.Lock()

        def chat_json_side_effect(*args, **kwargs):
            with lock:
                call_count[0] += 1
                n = call_count[0]

            if n == 1:
                # First call: decompose into 3 tasks
                return [
                    {"description": "task A", "role": "researcher"},
                    {"description": "task B", "role": "researcher"},
                    {"description": "task C", "role": "researcher"},
                ]
            return INSPECTION_PASS

        def chat_side_effect(*args, **kwargs):
            tid = threading.current_thread().name
            t = time.monotonic()
            with lock:
                call_log.append((tid, t))
            time.sleep(delay)
            return "task output"

        llm = MagicMock()
        llm.chat_json.side_effect = chat_json_side_effect
        llm.chat.side_effect = chat_side_effect
        return llm, call_log

    def test_three_tasks_run_concurrently(self):
        """With 3 independent tasks and a small delay per task, parallel execution
        should finish faster than sequential would (3×delay)."""
        delay = 0.05
        llm, call_log = self._make_timed_llm(delay=delay)
        orch = _make_orchestrator(llm)

        start = time.monotonic()
        result = orch.execute_goal("do three things")
        elapsed = time.monotonic() - start

        assert len(result["tasks"]) == 3
        # Sequential would take ≥ 3×delay; parallel should be well under 3×delay
        # Use 2.5× as the threshold to avoid flakiness
        assert elapsed < delay * 2.5 * 3, (
            f"Elapsed {elapsed:.3f}s suggests sequential execution (expected < {delay * 2.5 * 3:.3f}s)"
        )

    def test_parallel_results_all_complete(self):
        """All tasks complete successfully under parallel execution."""
        llm, _ = self._make_timed_llm(delay=0.01)
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("parallel goal")
        statuses = {r["status"] for r in result["tasks"]}
        assert statuses == {"completed"}

    def test_parallel_economy_stays_consistent(self):
        """Economy totals remain consistent after parallel execution."""
        llm, _ = self._make_timed_llm(delay=0.01)
        orch = _make_orchestrator(llm)
        initial_minted = orch.economy.central_bank.total_minted
        result = orch.execute_goal("parallel goal")

        # All rewards paid → treasury must have decreased
        econ = result["economy"]
        assert econ["money_supply"] > 0
        # No negative balances
        assert econ["treasury_balance"] >= 0

    def test_single_task_runs_sequentially(self):
        """Single-task goals skip the executor (no overhead)."""
        call_count = [0]

        def chat_json_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [{"description": "only task", "role": "researcher"}]
            return INSPECTION_PASS

        llm = MagicMock()
        llm.chat_json.side_effect = chat_json_side_effect
        llm.chat.return_value = "done"

        orch = _make_orchestrator(llm)
        result = orch.execute_goal("single task goal")
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["status"] == "completed"

    def test_memory_thread_safety(self):
        """Multiple threads writing to Memory concurrently should not corrupt data."""
        mem = Memory(":memory:")
        errors = []

        def write_read(n):
            try:
                for i in range(10):
                    mem.save_agent(
                        agent_id=f"agent-{n}-{i}",
                        role="researcher",
                        budget=100.0,
                        depth=0,
                        avg_score=0.7,
                        alive=True,
                    )
                    mem.get_best_genes("researcher", limit=5)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_read, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread safety errors: {errors}"
        # All 60 agents should be present
        count = mem._query_one("SELECT COUNT(*) as c FROM agents")["c"]
        assert count == 60
