"""Tests for silicon_realms.dynamics — theoretical dynamics enrichments."""
import math
import random
from dataclasses import field

from silicon_realms.models import Agent, SimState, Realm, Ledger
from silicon_realms.dynamics import (
    evolve_strategies,
    strategy_frequencies,
    compute_temperature,
    compute_entropy,
    update_thermodynamics,
    update_bellman_values,
    best_realm_by_value,
    detect_avalanche,
    avalanche_distribution,
    is_near_critical,
    compute_fisher_information,
    compute_kl_divergence,
    compute_natural_gradient,
    update_information_geometry,
    tick_dynamics,
)


# ─── Helpers ─────────────────────────────────────────────────────────────

def _make_state(
    agents: dict[str, Agent] | None = None,
    seed: int = 42,
    config: dict | None = None,
) -> SimState:
    """Build a minimal SimState for testing."""
    realms = {
        "compute": Realm(name="compute", capacity=50, base_reward=10),
        "memory": Realm(name="memory", capacity=40, base_reward=8),
        "network": Realm(name="network", capacity=30, base_reward=12),
        "information": Realm(name="information", capacity=35, base_reward=9),
    }
    state = SimState(
        realms=realms,
        agents=agents or {},
        rng=random.Random(seed),
        config=config or {},
    )
    return state


def _agent(name: str, balance: float, staked: float = 0, strategy: str = "balanced",
           realm: str = "compute", fitness_history: list | None = None) -> Agent:
    a = Agent(id=name, name=name, realm=realm, balance=balance, staked=staked, strategy=strategy)
    if fitness_history:
        a.fitness_history = fitness_history
    return a


# ─── 1. Replicator Dynamics ──────────────────────────────────────────────

class TestReplicatorDynamics:
    def test_strategy_frequencies_sums_to_one(self):
        agents = {
            "a": _agent("a", 100, strategy="aggressive"),
            "b": _agent("b", 100, strategy="aggressive"),
            "c": _agent("c", 100, strategy="balanced"),
        }
        state = _make_state(agents)
        freqs = strategy_frequencies(state)
        assert abs(sum(freqs.values()) - 1.0) < 1e-9

    def test_strategy_frequencies_correct_proportions(self):
        agents = {
            "a": _agent("a", 100, strategy="aggressive"),
            "b": _agent("b", 100, strategy="aggressive"),
            "c": _agent("c", 100, strategy="balanced"),
            "d": _agent("d", 100, strategy="conservative"),
        }
        state = _make_state(agents)
        freqs = strategy_frequencies(state)
        assert freqs["aggressive"] == 0.5
        assert freqs["balanced"] == 0.25
        assert freqs["conservative"] == 0.25

    def test_evolve_strategies_no_crash_on_empty(self):
        state = _make_state(agents={})
        evolve_strategies(state)  # should not crash

    def test_evolve_strategies_tracks_fitness(self):
        agents = {"a": _agent("a", 100), "b": _agent("b", 50)}
        state = _make_state(agents)
        evolve_strategies(state)
        assert len(state.agents["a"].fitness_history) == 1
        assert state.agents["a"].fitness_history[0] == 100

    def test_evolve_strategies_fitness_history_capped(self):
        a = _agent("a", 100, fitness_history=list(range(20)))
        state = _make_state({"a": a})
        evolve_strategies(state)
        assert len(state.agents["a"].fitness_history) == 20

    def test_low_fitness_agents_may_switch(self):
        """Run many iterations: a poor agent should eventually switch strategy."""
        rich = _agent("rich", 10000, strategy="aggressive")
        poor = _agent("poor", 1, strategy="conservative")
        agents = {"rich": rich, "poor": poor}
        state = _make_state(agents, config={"dynamics": {"mutation_rate": 1.0}})

        switched = False
        for _ in range(200):
            evolve_strategies(state)
            if state.agents["poor"].strategy != "conservative":
                switched = True
                break
        assert switched, "Poor agent should switch strategy with high mutation_rate"


# ─── 2. Statistical Mechanics ────────────────────────────────────────────

class TestStatisticalMechanics:
    def test_temperature_equal_wealth(self):
        """Equal wealth → T ≈ 0."""
        agents = {f"a{i}": _agent(f"a{i}", 100) for i in range(10)}
        state = _make_state(agents)
        t = compute_temperature(state)
        assert t < 0.01

    def test_temperature_unequal_wealth(self):
        """Very unequal wealth → high T."""
        agents = {
            "rich": _agent("rich", 10000),
            "poor1": _agent("poor1", 1),
            "poor2": _agent("poor2", 1),
        }
        state = _make_state(agents)
        t = compute_temperature(state)
        assert t > 0.5

    def test_temperature_edge_case_single_agent(self):
        state = _make_state({"a": _agent("a", 100)})
        assert compute_temperature(state) == 1.0

    def test_temperature_edge_case_zero_wealth(self):
        agents = {f"a{i}": _agent(f"a{i}", 0) for i in range(5)}
        state = _make_state(agents)
        assert compute_temperature(state) == 1.0  # fallback

    def test_entropy_equal_wealth(self):
        """Equal wealth → maximum entropy = log(n)."""
        n = 10
        agents = {f"a{i}": _agent(f"a{i}", 100) for i in range(n)}
        state = _make_state(agents)
        h = compute_entropy(state)
        assert abs(h - math.log(n)) < 1e-9

    def test_entropy_one_holds_all(self):
        """One agent holds everything → entropy ≈ 0."""
        agents = {"rich": _agent("rich", 1000), "poor": _agent("poor", 0)}
        state = _make_state(agents)
        h = compute_entropy(state)
        assert h < 0.01

    def test_entropy_zero_total_wealth(self):
        agents = {f"a{i}": _agent(f"a{i}", 0) for i in range(5)}
        state = _make_state(agents)
        assert compute_entropy(state) == 0.0

    def test_update_thermodynamics_sets_state(self):
        agents = {f"a{i}": _agent(f"a{i}", 100) for i in range(5)}
        state = _make_state(agents)
        update_thermodynamics(state)
        assert state.temperature >= 0
        assert state.entropy >= 0


# ─── 3. Bellman Value Function ───────────────────────────────────────────

class TestBellmanValues:
    def test_initial_values_zero(self):
        state = _make_state()
        update_bellman_values(state)
        for v in state.realm_values.values():
            assert v == 0.0

    def test_positive_reward_increases_value(self):
        agents = {
            "a": _agent("a", 100, realm="compute",
                        fitness_history=[90, 100]),
        }
        state = _make_state(agents)
        update_bellman_values(state)
        assert state.realm_values["compute"] > 0

    def test_negative_reward_decreases_value(self):
        agents = {
            "a": _agent("a", 50, realm="memory",
                        fitness_history=[100, 50]),
        }
        state = _make_state(agents)
        update_bellman_values(state)
        assert state.realm_values["memory"] < 0

    def test_best_realm_by_value(self):
        state = _make_state()
        state.realm_values = {"compute": 5.0, "memory": 2.0, "network": 8.0}
        assert best_realm_by_value(state) == "network"

    def test_best_realm_by_value_empty(self):
        state = _make_state()
        state.realm_values = {}
        # Should not crash, returns a valid realm
        result = best_realm_by_value(state)
        assert result in ["compute", "memory", "network", "information"]


# ─── 4. Self-Organized Criticality ──────────────────────────────────────

class TestSOC:
    def test_detect_avalanche_no_history(self):
        agents = {"a": _agent("a", 100)}
        state = _make_state(agents)
        drop = detect_avalanche(state)
        assert drop == 0.0

    def test_detect_avalanche_with_drop(self):
        agents = {
            "a": _agent("a", 50, fitness_history=[200, 50]),
            "b": _agent("b", 100, fitness_history=[100, 90]),
        }
        state = _make_state(agents)
        drop = detect_avalanche(state)
        assert drop == 150  # 200 - 50
        assert state.last_avalanche_size == 150

    def test_detect_avalanche_no_drop(self):
        """All agents gained wealth → max drop = 0."""
        agents = {
            "a": _agent("a", 200, fitness_history=[100, 200]),
        }
        state = _make_state(agents)
        drop = detect_avalanche(state)
        assert drop == 0.0

    def test_avalanche_distribution_empty(self):
        agents = {"a": _agent("a", 100)}
        state = _make_state(agents)
        assert avalanche_distribution(state) == {}

    def test_avalanche_distribution_bins(self):
        agents = {
            "a": _agent("a", 50, fitness_history=[50.5, 50]),   # drop 0.5
            "b": _agent("b", 95, fitness_history=[100, 95]),    # drop 5
            "c": _agent("c", 50, fitness_history=[100, 50]),    # drop 50
        }
        state = _make_state(agents)
        dist = avalanche_distribution(state)
        assert dist["0-1"] == 1
        assert dist["1-10"] == 1
        assert dist["10-100"] == 1

    def test_is_near_critical_true(self):
        agents = {f"a{i}": _agent(f"a{i}", 100 + i * 10) for i in range(20)}
        state = _make_state(agents)
        update_thermodynamics(state)
        # Force moderate temperature
        state.temperature = 0.8
        # Entropy should already be high with 20 agents of similar wealth
        n = len(state.agents)
        max_h = math.log(n)
        state.entropy = max_h * 0.8
        assert is_near_critical(state)

    def test_is_near_critical_false_extreme_temp(self):
        state = _make_state({f"a{i}": _agent(f"a{i}", 100) for i in range(10)})
        state.temperature = 5.0  # too hot
        state.entropy = math.log(10) * 0.9
        assert not is_near_critical(state)


# ─── 5. Combined tick ───────────────────────────────────────────────────

# ─── 5. Information Geometry ───────────────────────────────────────────

class TestInformationGeometry:
    def test_fisher_information_no_history(self):
        """No fitness history → Fisher info = 0."""
        agents = {f"a{i}": _agent(f"a{i}", 100) for i in range(5)}
        state = _make_state(agents)
        fi = compute_fisher_information(state)
        assert fi == 0.0

    def test_fisher_information_stable_economy(self):
        """Stable wealth (no change) → low Fisher info."""
        agents = {f"a{i}": _agent(f"a{i}", 100, fitness_history=[100, 100])
                  for i in range(5)}
        state = _make_state(agents)
        fi = compute_fisher_information(state)
        assert fi < 0.01

    def test_fisher_information_volatile_economy(self):
        """Large wealth shifts → high Fisher info."""
        agents = {
            "a": _agent("a", 200, fitness_history=[50, 200]),
            "b": _agent("b", 50, fitness_history=[200, 50]),
        }
        state = _make_state(agents)
        fi = compute_fisher_information(state)
        assert fi > 0.1

    def test_fisher_info_empty(self):
        state = _make_state(agents={})
        assert compute_fisher_information(state) == 0.0

    def test_kl_divergence_equal_wealth(self):
        """Equal wealth → KL divergence = 0."""
        n = 10
        agents = {f"a{i}": _agent(f"a{i}", 100) for i in range(n)}
        state = _make_state(agents)
        update_thermodynamics(state)
        kl = compute_kl_divergence(state)
        assert abs(kl) < 1e-9

    def test_kl_divergence_unequal_wealth(self):
        """Concentrated wealth → high KL divergence."""
        agents = {
            "rich": _agent("rich", 10000),
            "poor1": _agent("poor1", 0),
            "poor2": _agent("poor2", 0),
        }
        state = _make_state(agents)
        update_thermodynamics(state)
        kl = compute_kl_divergence(state)
        assert kl > 0.5

    def test_kl_divergence_single_agent(self):
        state = _make_state({"a": _agent("a", 100)})
        assert compute_kl_divergence(state) == 0.0

    def test_natural_gradient_computed_per_realm(self):
        agents = {
            "a": _agent("a", 100, realm="compute", fitness_history=[80, 100]),
            "b": _agent("b", 50, realm="memory", fitness_history=[60, 50]),
            "c": _agent("c", 200, realm="information", fitness_history=[150, 200]),
        }
        state = _make_state(agents)
        state.fisher_information = 0.5
        grad = compute_natural_gradient(state)
        assert "compute" in grad
        assert "memory" in grad
        assert "network" in grad
        assert "information" in grad

    def test_natural_gradient_dampened_by_fisher(self):
        """High Fisher info should dampen the gradient."""
        agents = {"a": _agent("a", 200, realm="compute", fitness_history=[100, 200])}
        state = _make_state(agents)

        state.fisher_information = 0.0
        grad_low = compute_natural_gradient(state)

        state.fisher_information = 10.0
        grad_high = compute_natural_gradient(state)

        # High Fisher → smaller gradient magnitude
        assert abs(grad_high["compute"]) < abs(grad_low["compute"])

    def test_update_information_geometry_sets_state(self):
        agents = {f"a{i}": _agent(f"a{i}", 100 + i * 10, fitness_history=[90 + i * 10, 100 + i * 10])
                  for i in range(5)}
        state = _make_state(agents)
        update_thermodynamics(state)  # needed for KL divergence
        update_information_geometry(state)
        assert state.fisher_information >= 0
        assert state.kl_divergence >= 0
        assert isinstance(state.natural_gradient, dict)


# ─── 6. Combined tick ───────────────────────────────────────────────────

class TestTickDynamics:
    def test_tick_dynamics_runs(self):
        """tick_dynamics should run all five subsystems without error."""
        realms = ["compute", "memory", "network", "information"]
        agents = {
            f"a{i}": _agent(f"a{i}", 100 + i * 20, realm=realms[i % 4],
                            fitness_history=[80 + i * 10, 100 + i * 20])
            for i in range(12)
        }
        state = _make_state(agents)
        tick_dynamics(state)

        # Thermodynamics ran
        assert state.temperature >= 0
        assert state.entropy >= 0
        # Bellman ran
        assert len(state.realm_values) == 4
        # SOC ran
        assert hasattr(state, "last_avalanche_size")
        # Information geometry ran
        assert state.fisher_information >= 0
        assert state.kl_divergence >= 0
        assert len(state.natural_gradient) == 4
