"""Tests for Attention/Resource Allocation as Theory Parameter."""

from __future__ import annotations

import pytest

from zhihuiti.collision import THEORIES
from zhihuiti.memory import Memory
from zhihuiti.models import Realm
from zhihuiti.realms import RealmManager, REALM_BUDGET_RATIO


@pytest.fixture
def mem():
    return Memory(":memory:")


@pytest.fixture
def realm_mgr(mem):
    return RealmManager(mem)


class TestTheoryAttentionConfig:
    def test_all_theories_have_attention(self):
        """Every theory must define attention allocation ratios."""
        for name, config in THEORIES.items():
            assert "attention" in config, f"Theory '{name}' missing 'attention'"
            att = config["attention"]
            assert "research" in att
            assert "execution" in att
            assert "central" in att
            # Ratios must sum to 1.0 (with floating point tolerance)
            total = att["research"] + att["execution"] + att["central"]
            assert abs(total - 1.0) < 0.01, f"Theory '{name}' attention sums to {total}"

    def test_darwinian_favors_execution(self):
        att = THEORIES["darwinian"]["attention"]
        assert att["execution"] > att["research"]

    def test_mutualist_favors_research(self):
        att = THEORIES["mutualist"]["attention"]
        assert att["research"] > att["execution"]

    def test_hybrid_matches_defaults(self):
        att = THEORIES["hybrid"]["attention"]
        # Hybrid should be similar to default REALM_BUDGET_RATIO
        assert att["research"] == REALM_BUDGET_RATIO[Realm.RESEARCH]
        assert att["execution"] == REALM_BUDGET_RATIO[Realm.EXECUTION]
        assert att["central"] == REALM_BUDGET_RATIO[Realm.CENTRAL]

    def test_elitist_favors_execution(self):
        att = THEORIES["elitist"]["attention"]
        assert att["execution"] > att["research"]


class TestDynamicBudgetAllocation:
    def test_default_allocation(self, realm_mgr):
        realm_mgr.allocate_budgets(1000.0)
        research = realm_mgr.realms[Realm.RESEARCH].budget_allocated
        execution = realm_mgr.realms[Realm.EXECUTION].budget_allocated
        central = realm_mgr.realms[Realm.CENTRAL].budget_allocated
        assert research == pytest.approx(500.0)
        assert execution == pytest.approx(350.0)
        assert central == pytest.approx(150.0)

    def test_custom_attention_allocation(self, realm_mgr):
        attention = {"research": 0.70, "execution": 0.20, "central": 0.10}
        realm_mgr.allocate_budgets(1000.0, attention=attention)
        research = realm_mgr.realms[Realm.RESEARCH].budget_allocated
        execution = realm_mgr.realms[Realm.EXECUTION].budget_allocated
        central = realm_mgr.realms[Realm.CENTRAL].budget_allocated
        assert research == pytest.approx(700.0)
        assert execution == pytest.approx(200.0)
        assert central == pytest.approx(100.0)

    def test_darwinian_attention(self, realm_mgr):
        att = THEORIES["darwinian"]["attention"]
        realm_mgr.allocate_budgets(1000.0, attention=att)
        execution = realm_mgr.realms[Realm.EXECUTION].budget_allocated
        research = realm_mgr.realms[Realm.RESEARCH].budget_allocated
        assert execution > research  # Darwinian favors execution

    def test_mutualist_attention(self, realm_mgr):
        att = THEORIES["mutualist"]["attention"]
        realm_mgr.allocate_budgets(1000.0, attention=att)
        research = realm_mgr.realms[Realm.RESEARCH].budget_allocated
        execution = realm_mgr.realms[Realm.EXECUTION].budget_allocated
        assert research > execution  # Mutualist favors research

    def test_cumulative_allocation(self, realm_mgr):
        """Multiple allocations should accumulate."""
        realm_mgr.allocate_budgets(500.0)
        realm_mgr.allocate_budgets(500.0)
        total = sum(
            realm_mgr.realms[r].budget_allocated for r in Realm
        )
        assert total == pytest.approx(1000.0)
