"""Tests for evolutionary simulation."""

import json
from unittest.mock import MagicMock, patch

from zhihuiti.genome import StrategyGenome, random_genome, classify_archetype
from zhihuiti.simulation import (
    EvolutionarySimulation,
    SimulationConfig,
    AgentDecision,
    EpochStats,
    MAINTENANCE_COST,
    EVOLVED_BANKRUPTCY,
    POPULATION_FLOOR,
)


def _make_sim(population: int = 10, db: str = ":memory:") -> EvolutionarySimulation:
    config = SimulationConfig(
        population_size=population,
        epochs=5,
        model="haiku",
        max_cost_usd=100.0,
        concurrency=1,
        db_path=db,
    )
    sim = EvolutionarySimulation(config)
    return sim


def test_generate_tasks():
    sim = _make_sim()
    tasks = sim._generate_tasks(1)
    assert 10 <= len(tasks) <= 20
    for t in tasks:
        assert "id" in t
        assert "role" in t
        assert "complexity" in t
        assert "price_ceiling" in t
        assert t["complexity"] >= 0.5
        assert t["price_ceiling"] > 0


def test_genome_heuristic_high_aggression_bids():
    sim = _make_sim()
    sim.initialize_population()
    agent = list(sim.agents.values())[0]
    agent.config.genome = StrategyGenome(bid_aggression=0.8)
    tasks = sim._generate_tasks(1)
    decision = sim._genome_heuristic(agent, tasks)
    assert decision.action == "bid"
    assert "task_id" in decision.params


def test_genome_heuristic_low_aggression_skips():
    sim = _make_sim()
    sim.initialize_population()
    agent = list(sim.agents.values())[0]
    agent.config.genome = StrategyGenome(bid_aggression=0.2)
    tasks = sim._generate_tasks(1)
    decision = sim._genome_heuristic(agent, tasks)
    assert decision.action == "skip"


def test_score_task_role_match():
    sim = _make_sim()
    sim.initialize_population()
    agent = list(sim.agents.values())[0]
    task = {"role": agent.config.role, "complexity": 1.0}
    scores = [sim._score_task(agent, task) for _ in range(100)]
    avg = sum(scores) / len(scores)
    assert avg > 0.5  # Role match should produce decent scores


def test_fitness_blended_score():
    sim = _make_sim()
    sim.initialize_population()
    agent = list(sim.agents.values())[0]
    agent.fitness = 0.5
    agent.budget = 120.0  # Gained 20 tokens
    sim._update_fitness(agent, task_score=0.8, budget_start=100.0)
    # EMA: 0.8 * 0.5 + 0.2 * (0.7*0.8 + 0.3*0.2) = 0.4 + 0.2*(0.56+0.06) = 0.4 + 0.124 = 0.524
    assert 0.4 < agent.fitness < 0.7


def test_fitness_ema_update():
    sim = _make_sim()
    sim.initialize_population()
    agent = list(sim.agents.values())[0]
    agent.fitness = 0.5
    agent.budget = 100.0
    sim._update_fitness(agent, task_score=1.0, budget_start=100.0)
    # 0.8 * 0.5 + 0.2 * (0.7 * 1.0 + 0.3 * 0.0) = 0.4 + 0.14 = 0.54
    assert abs(agent.fitness - 0.54) < 0.01


def test_fitness_skip_gives_zero_task_score():
    sim = _make_sim()
    sim.initialize_population()
    agent = list(sim.agents.values())[0]
    agent.fitness = 0.8
    agent.budget = 90.0  # Lost 10 from maintenance
    sim._update_fitness(agent, task_score=0.0, budget_start=100.0)
    # Fitness should decrease
    assert agent.fitness < 0.8


def test_natural_selection_culls_bankrupts():
    sim = _make_sim(population=15)
    sim.initialize_population()
    # Make some agents bankrupt
    for i, agent in enumerate(list(sim.agents.values())):
        if i < 5:
            agent.budget = 1.0  # Below EVOLVED_BANKRUPTCY threshold

    culled, born = sim._natural_selection()
    assert len(culled) == 5


def test_natural_selection_breeds_top():
    sim = _make_sim(population=20)
    sim.initialize_population()
    # Set varied fitness
    for i, agent in enumerate(sim.agents.values()):
        agent.fitness = (i + 1) / 20.0

    initial_count = len(sim.agents)
    culled, born = sim._natural_selection()
    # Top 20% = 4 agents, breeding in pairs = 2 children
    assert len(born) >= 1


def test_population_floor_emergency_spawn():
    sim = _make_sim(population=5)
    sim.initialize_population()
    # Kill most agents
    for agent in list(sim.agents.values()):
        agent.budget = 0.5  # Below threshold

    culled, born = sim._natural_selection()
    alive = sum(1 for a in sim.agents.values() if a.alive)
    assert alive >= POPULATION_FLOOR


@patch("zhihuiti.simulation.EvolutionarySimulation._agent_decision")
def test_run_epoch_integration(mock_decision):
    """Full epoch with mock LLM decisions."""
    mock_decision.return_value = AgentDecision(
        action="skip", reasoning="test"
    )
    sim = _make_sim(population=10)
    sim.initialize_population()
    stats = sim.run_epoch()
    assert isinstance(stats, EpochStats)
    assert stats.epoch == 1
    assert stats.population > 0


@patch("zhihuiti.simulation.EvolutionarySimulation._agent_decision")
def test_cost_cap_halts(mock_decision):
    """Simulation stops when cost cap is reached."""
    mock_decision.return_value = AgentDecision(
        action="skip", reasoning="test"
    )
    config = SimulationConfig(
        population_size=5,
        epochs=100,
        max_cost_usd=0.001,  # Very low cap
        concurrency=1,
        db_path=":memory:",
    )
    sim = EvolutionarySimulation(config)
    sim.total_cost_usd = 0.002  # Already over cap
    sim.initialize_population()
    stats = sim.run(n_epochs=100)
    assert len(stats) == 0  # Should halt immediately


def test_parse_llm_response_valid_json():
    sim = _make_sim()
    response = '{"action": "bid", "params": {"task_id": "abc", "amount": 12.5}, "reasoning": "I bid"}'
    decision = sim._parse_llm_response(response)
    assert decision.action == "bid"
    assert decision.params["task_id"] == "abc"


def test_parse_llm_response_malformed():
    sim = _make_sim()
    decision = sim._parse_llm_response("not json at all")
    assert decision.action == "skip"


def test_parse_llm_response_markdown_code_block():
    sim = _make_sim()
    response = '```json\n{"action": "skip", "params": {}, "reasoning": "conserving"}\n```'
    decision = sim._parse_llm_response(response)
    assert decision.action == "skip"


def test_gini_coefficient():
    # Equal distribution → Gini = 0
    assert abs(EvolutionarySimulation._calculate_gini([100, 100, 100])) < 0.01
    # Perfect inequality → Gini approaches 1
    gini = EvolutionarySimulation._calculate_gini([0, 0, 0, 0, 1000])
    assert gini > 0.5
