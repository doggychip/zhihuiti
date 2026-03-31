"""Tests for Metacognition Engine — automatic regime switching."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from zhihuiti.metacognition import (
    MetacognitionEngine,
    RegimeRecommendation,
    CONFIDENCE_THRESHOLD,
    DEFAULT_THEORY,
    DOMAIN_KEYWORDS,
    MIN_OBSERVATIONS,
)
from zhihuiti.memory import Memory


@pytest.fixture
def mem():
    return Memory(":memory:")


@pytest.fixture
def engine(mem):
    return MetacognitionEngine(mem)


class TestDomainClassification:
    def test_classify_trading(self, engine):
        assert engine.classify_domain("trade BTC on the market") == "trading"

    def test_classify_research(self, engine):
        assert engine.classify_domain("research the hypothesis about AI") == "research"

    def test_classify_coding(self, engine):
        assert engine.classify_domain("implement a new API function") == "coding"

    def test_classify_content(self, engine):
        assert engine.classify_domain("write a blog article about AI") == "content"

    def test_classify_strategy(self, engine):
        assert engine.classify_domain("design the roadmap for next quarter") == "strategy"

    def test_classify_general(self, engine):
        assert engine.classify_domain("do something vague") == "general"

    def test_classify_multi_keyword(self, engine):
        # Should pick the domain with the most keyword hits
        result = engine.classify_domain("research and analyze market price data")
        assert result in ("trading", "research")


class TestRecordCollision:
    def test_record_collision_persists(self, engine, mem):
        engine.record_collision(
            goal="trade BTC",
            theory_a="darwinian",
            theory_b="mutualist",
            score_a=0.8,
            score_b=0.6,
            winner="darwinian",
        )
        history = mem.get_collision_history()
        assert len(history) == 1
        assert history[0]["domain"] == "trading"
        assert history[0]["winner"] == "darwinian"

    def test_record_collision_updates_preferences(self, engine, mem):
        engine.record_collision(
            goal="trade BTC", theory_a="darwinian", theory_b="mutualist",
            score_a=0.8, score_b=0.6, winner="darwinian",
        )
        prefs = mem.get_all_regime_preferences()
        assert len(prefs) >= 1
        # Darwinian should have a win recorded
        darwinian_pref = [p for p in prefs if p["theory"] == "darwinian"]
        assert len(darwinian_pref) == 1
        assert darwinian_pref[0]["win_count"] == 1

    def test_multiple_collisions_accumulate(self, engine, mem):
        for _ in range(5):
            engine.record_collision(
                goal="trade ETH on the market",
                theory_a="darwinian", theory_b="mutualist",
                score_a=0.85, score_b=0.65, winner="darwinian",
            )
        prefs = mem.get_all_regime_preferences()
        darwinian = [p for p in prefs if p["theory"] == "darwinian" and p["domain"] == "trading"]
        assert darwinian[0]["win_count"] == 5
        assert darwinian[0]["total_count"] == 5


class TestRecommendation:
    def test_no_data_returns_default(self, engine):
        rec = engine.recommend("trade BTC")
        assert rec.theory == DEFAULT_THEORY
        assert rec.confidence == 0.0

    def test_low_confidence_returns_default(self, engine):
        # One observation isn't enough
        engine.record_collision(
            goal="trade BTC", theory_a="darwinian", theory_b="mutualist",
            score_a=0.9, score_b=0.5, winner="darwinian",
        )
        rec = engine.recommend("trade ETH on the market")
        assert rec.theory == DEFAULT_THEORY

    def test_sufficient_data_recommends(self, engine):
        # Record enough collisions to build confidence
        for i in range(MIN_OBSERVATIONS + 2):
            engine.record_collision(
                goal="trade crypto on the market",
                theory_a="darwinian", theory_b="mutualist",
                score_a=0.85, score_b=0.65, winner="darwinian",
            )
        rec = engine.recommend("trade BTC on the market")
        assert rec.theory == "darwinian"
        assert rec.confidence >= CONFIDENCE_THRESHOLD

    def test_recommendation_to_dict(self, engine):
        rec = RegimeRecommendation(
            domain="trading", theory="darwinian", confidence=0.8,
            win_rate=0.9, avg_score=0.85, observation_count=10,
            reason="test",
        )
        d = rec.to_dict()
        assert d["domain"] == "trading"
        assert d["theory"] == "darwinian"
        assert "observations" in d


class TestGetTheoryConfig:
    def test_returns_valid_config(self, engine):
        config, rec = engine.get_theory_config("trade BTC")
        assert "cull_threshold" in config
        assert "promote_threshold" in config
        assert "messaging" in config
        assert "lending" in config
        assert "attention" in config

    def test_falls_back_to_hybrid(self, engine):
        config, rec = engine.get_theory_config("something unknown")
        assert rec.theory == DEFAULT_THEORY


class TestReporting:
    def test_print_report_no_crash(self, engine, capsys):
        engine.print_report()  # Should not crash with no data

    def test_print_report_with_data(self, engine, capsys):
        engine.record_collision(
            goal="trade BTC", theory_a="darwinian", theory_b="mutualist",
            score_a=0.8, score_b=0.6, winner="darwinian",
        )
        engine.print_report()  # Should not crash
