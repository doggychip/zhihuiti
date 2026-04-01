"""Tests for strategy genome operations."""

import random

from zhihuiti.genome import (
    StrategyGenome,
    classify_archetype,
    crossover,
    mutate,
    random_genome,
)


def test_random_genome_traits_in_bounds():
    random.seed(42)
    for _ in range(100):
        g = random_genome()
        for val in g.to_dict().values():
            assert 0.0 <= val <= 1.0


def test_crossover_equal_bias_produces_midpoint():
    a = StrategyGenome(bid_aggression=0.0, risk_tolerance=0.0,
                       cooperation_bias=0.0, specialization=0.0,
                       price_sensitivity=0.0, breeding_investment=0.0)
    b = StrategyGenome(bid_aggression=1.0, risk_tolerance=1.0,
                       cooperation_bias=1.0, specialization=1.0,
                       price_sensitivity=1.0, breeding_investment=1.0)
    child = crossover(a, b, bias=0.5)
    for val in child.to_dict().values():
        assert abs(val - 0.5) < 1e-9


def test_crossover_full_bias_clones_parent_a():
    a = StrategyGenome(bid_aggression=0.2, risk_tolerance=0.8,
                       cooperation_bias=0.3, specialization=0.9,
                       price_sensitivity=0.1, breeding_investment=0.7)
    b = random_genome()
    child = crossover(a, b, bias=1.0)
    assert child.to_dict() == a.to_dict()


def test_crossover_result_in_bounds():
    random.seed(123)
    for _ in range(100):
        a = random_genome()
        b = random_genome()
        child = crossover(a, b, bias=random.random())
        for val in child.to_dict().values():
            assert 0.0 <= val <= 1.0


def test_mutate_rate_zero_produces_identical():
    g = StrategyGenome(bid_aggression=0.3, risk_tolerance=0.7,
                       cooperation_bias=0.5, specialization=0.2,
                       price_sensitivity=0.8, breeding_investment=0.1)
    mutated = mutate(g, rate=0.0)
    assert mutated.to_dict() == g.to_dict()


def test_mutate_rate_one_always_mutates():
    random.seed(42)
    g = StrategyGenome(bid_aggression=0.5, risk_tolerance=0.5,
                       cooperation_bias=0.5, specialization=0.5,
                       price_sensitivity=0.5, breeding_investment=0.5)
    mutated = mutate(g, rate=1.0)
    # With rate=1.0, at least some traits should differ
    diffs = sum(1 for k in g.to_dict() if g.to_dict()[k] != mutated.to_dict()[k])
    assert diffs > 0


def test_mutate_output_clamped():
    random.seed(99)
    # Start at extremes to test clamping
    g = StrategyGenome(bid_aggression=0.0, risk_tolerance=1.0,
                       cooperation_bias=0.0, specialization=1.0,
                       price_sensitivity=0.0, breeding_investment=1.0)
    for _ in range(100):
        mutated = mutate(g, rate=1.0)
        for val in mutated.to_dict().values():
            assert 0.0 <= val <= 1.0


def test_classify_specialist():
    g = StrategyGenome(specialization=0.9, bid_aggression=0.2,
                       cooperation_bias=0.5, risk_tolerance=0.5,
                       price_sensitivity=0.5, breeding_investment=0.5)
    assert classify_archetype(g) == "specialist"


def test_classify_predator():
    g = StrategyGenome(bid_aggression=0.9, cooperation_bias=0.1,
                       specialization=0.5, risk_tolerance=0.5,
                       price_sensitivity=0.5, breeding_investment=0.5)
    assert classify_archetype(g) == "predator"


def test_classify_trader():
    g = StrategyGenome(cooperation_bias=0.9, breeding_investment=0.8,
                       bid_aggression=0.5, specialization=0.5,
                       risk_tolerance=0.5, price_sensitivity=0.5)
    assert classify_archetype(g) == "trader"


def test_classify_generalist():
    g = StrategyGenome()  # all defaults at 0.5
    assert classify_archetype(g) == "generalist"


def test_to_dict_from_dict_roundtrip():
    g = random_genome()
    d = g.to_dict()
    g2 = StrategyGenome.from_dict(d)
    assert g.to_dict() == g2.to_dict()
