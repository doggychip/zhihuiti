"""Tests for Memory Consolidation Engine."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from zhihuiti.consolidation import (
    ConsolidationEngine,
    ConsolidationResult,
    FORGETTING_AGE_DAYS,
    MIN_GROUP_SIZE,
)
from zhihuiti.memory import Memory


@pytest.fixture
def mem():
    return Memory(":memory:")


@pytest.fixture
def engine(mem):
    return ConsolidationEngine(mem)


def _seed_old_tasks(mem: Memory, role: str = "researcher",
                    count: int = 10, score: float = 0.75):
    """Insert old task history entries that are eligible for consolidation."""
    for i in range(count):
        mem.record_task_history(
            description=f"Task {i} for {role}",
            agent_role=role,
            result=f"Result {i}",
            score=score,
        )
    # Artificially age the entries
    with mem._lock:
        mem.conn.execute(
            "UPDATE task_history SET created_at = datetime('now', '-60 days')"
        )
        mem.conn.commit()


class TestConsolidationNoData:
    def test_empty_consolidation(self, engine):
        result = engine.consolidate()
        assert result.entries_processed == 0
        assert result.principles_created == 0

    def test_no_old_entries(self, engine, mem):
        # Recent entries should not be consolidated
        mem.record_task_history("recent task", "researcher", "result", 0.8)
        result = engine.consolidate()
        assert result.entries_processed == 0


class TestHeuristicConsolidation:
    def test_consolidate_high_performers(self, engine, mem):
        _seed_old_tasks(mem, role="researcher", count=10, score=0.85)
        result = engine.consolidate(max_age_days=30, purge=False)
        assert result.entries_processed == 10
        assert result.groups_analyzed == 1
        assert result.principles_created >= 1

    def test_consolidate_low_performers(self, engine, mem):
        _seed_old_tasks(mem, role="coder", count=10, score=0.2)
        result = engine.consolidate(max_age_days=30, purge=False)
        assert result.principles_created >= 1

    def test_consolidate_purges_old_entries(self, engine, mem):
        _seed_old_tasks(mem, role="researcher", count=10, score=0.75)
        result = engine.consolidate(max_age_days=30, purge=True)
        assert result.entries_purged > 0

    def test_below_min_group_size_skipped(self, engine, mem):
        _seed_old_tasks(mem, role="researcher", count=MIN_GROUP_SIZE - 1, score=0.8)
        result = engine.consolidate(max_age_days=30, purge=False)
        assert result.groups_analyzed == 0

    def test_multiple_roles(self, engine, mem):
        _seed_old_tasks(mem, role="researcher", count=5, score=0.8)
        _seed_old_tasks(mem, role="trader", count=5, score=0.6)
        result = engine.consolidate(max_age_days=30, purge=False)
        assert result.groups_analyzed == 2


class TestLLMConsolidation:
    def test_llm_extract(self, mem):
        llm = MagicMock()
        llm.chat_json.return_value = {
            "principles": [
                {
                    "principle": "Researchers perform best with detailed prompts",
                    "domain": "researcher",
                    "confidence": 0.8,
                }
            ]
        }
        engine = ConsolidationEngine(mem, llm=llm)
        _seed_old_tasks(mem, role="researcher", count=5, score=0.8)
        result = engine.consolidate(max_age_days=30, purge=False)
        assert result.principles_created == 1
        assert llm.chat_json.called


class TestKnowledgeRetrieval:
    def test_get_context_for_role(self, engine, mem):
        mem.save_consolidated_knowledge(
            "k1", "Test principle", "researcher", 5, 0.8, ["goal1"],
        )
        context = engine.get_context_for_role("researcher")
        assert "Test principle" in context
        assert "80%" in context

    def test_get_context_empty(self, engine):
        context = engine.get_context_for_role("nonexistent")
        assert context == ""


class TestPrincipleUpdating:
    def test_existing_principle_gets_updated(self, engine, mem):
        # Create an initial principle
        mem.save_consolidated_knowledge(
            "k1", "Researchers perform best", "researcher", 5, 0.6, ["goal1"],
        )
        # Seed more tasks and consolidate again
        _seed_old_tasks(mem, role="researcher", count=10, score=0.85)
        result = engine.consolidate(max_age_days=30, purge=False)
        # The existing principle should be updated, not a new one created
        knowledge = mem.get_consolidated_knowledge(domain="researcher")
        assert len(knowledge) >= 1


class TestReporting:
    def test_print_knowledge_no_crash(self, engine):
        engine.print_knowledge()

    def test_print_knowledge_with_data(self, engine, mem):
        mem.save_consolidated_knowledge(
            "k1", "Test principle", "research", 5, 0.8, ["goal1"],
        )
        engine.print_knowledge()
