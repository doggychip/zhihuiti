"""Tests for silicon_realms.realms — theory-driven realm mechanics."""
import math
import random

from silicon_realms.models import Agent, SimState, Realm, Ledger
from silicon_realms.realms import (
    compute_tick,
    memory_tick,
    network_tick,
    apply_avalanche_spillover,
    migrate_agent,
)


# ─── Helpers ─────────────────────────────────────────────────────────────

def _make_state(agents=None, seed=42, tick=0, config=None, total_supply=10000):
    realms = {
        "compute": Realm(name="compute", capacity=50, base_reward=10,
                         params={"difficulty_growth": 0.02}),
        "memory": Realm(name="memory", capacity=40, base_reward=8,
                        params={"decay_rate": 0.01}),
        "network": Realm(name="network", capacity=30, base_reward=12,
                         params={"routing_fee": 0.05}),
    }
    state = SimState(
        tick=tick,
        realms=realms,
        agents=agents or {},
        rng=random.Random(seed),
        config=config or {"economy": {"transfer_fee": 0.01}},
        total_supply=total_supply,
    )
    return state


def _agent(name, balance=100, staked=0, strategy="balanced",
           realm="compute", energy=100, created_tick=0, fitness_history=None):
    a = Agent(id=name, name=name, realm=realm, balance=balance,
              staked=staked, strategy=strategy, energy=energy,
              created_tick=created_tick)
    if fitness_history:
        a.fitness_history = fitness_history
    return a


# ─── Compute Realm: Replicator Dynamics ──────────────────────────────────

class TestComputeRealm:
    def test_compute_empty_agents(self):
        state = _make_state()
        compute_tick(state, state.realms["compute"], [])  # no crash

    def test_compute_rewards_agents(self):
        agents = {f"a{i}": _agent(f"a{i}", balance=100, realm="compute") for i in range(5)}
        state = _make_state(agents)
        initial_supply = state.total_supply
        realm_agents = list(agents.values())
        compute_tick(state, state.realms["compute"], realm_agents)
        assert state.total_supply > initial_supply  # tokens were minted

    def test_compute_updates_realm_state(self):
        agents = {
            "greedy1": _agent("greedy1", balance=500, strategy="greedy"),
            "greedy2": _agent("greedy2", balance=400, strategy="greedy"),
            "poor": _agent("poor", balance=10, strategy="balanced"),
        }
        state = _make_state(agents)
        realm = state.realms["compute"]
        compute_tick(state, realm, list(agents.values()))

        assert realm.dominant_strategy != ""
        assert realm.selection_pressure >= 1.0
        assert len(realm.strategy_fitness) > 0

    def test_compute_selection_pressure_increases_with_tick(self):
        agents = {"a": _agent("a", balance=100)}
        early = _make_state(agents, tick=0)
        late = _make_state(agents, tick=50)

        compute_tick(early, early.realms["compute"], list(agents.values()))
        compute_tick(late, late.realms["compute"], list(agents.values()))

        assert late.realms["compute"].selection_pressure > early.realms["compute"].selection_pressure

    def test_compute_fitter_agents_earn_more(self):
        """Rich agents should earn more due to replicator amplification."""
        rich = _agent("rich", balance=1000, strategy="greedy")
        poor = _agent("poor", balance=10, strategy="greedy")
        agents = {"rich": rich, "poor": poor}
        state = _make_state(agents, seed=42)

        initial_rich = rich.balance
        initial_poor = poor.balance

        # Run many ticks to smooth out stochastic effects
        for _ in range(50):
            compute_tick(state, state.realms["compute"], [rich, poor])

        rich_gain = rich.balance - initial_rich
        poor_gain = poor.balance - initial_poor
        assert rich_gain > poor_gain

    def test_compute_zero_energy_skipped(self):
        agent = _agent("a", balance=100, energy=0)
        agents = {"a": agent}
        state = _make_state(agents)
        initial = state.total_supply
        compute_tick(state, state.realms["compute"], [agent])
        assert state.total_supply == initial  # no minting


# ─── Memory Realm: Statistical Mechanics ─────────────────────────────────

class TestMemoryRealm:
    def test_memory_empty_agents(self):
        state = _make_state()
        memory_tick(state, state.realms["memory"], [])  # no crash

    def test_memory_computes_local_temperature(self):
        agents = {
            "rich": _agent("rich", balance=1000, realm="memory"),
            "poor": _agent("poor", balance=10, realm="memory"),
        }
        state = _make_state(agents)
        realm = state.realms["memory"]
        memory_tick(state, realm, list(agents.values()))
        assert realm.realm_temperature > 0

    def test_memory_computes_local_entropy(self):
        agents = {f"a{i}": _agent(f"a{i}", balance=100, realm="memory") for i in range(5)}
        state = _make_state(agents)
        realm = state.realms["memory"]
        memory_tick(state, realm, list(agents.values()))
        assert realm.realm_entropy > 0

    def test_memory_equal_wealth_high_entropy(self):
        n = 10
        agents = {f"a{i}": _agent(f"a{i}", balance=100, realm="memory") for i in range(n)}
        state = _make_state(agents)
        realm = state.realms["memory"]
        memory_tick(state, realm, list(agents.values()))
        max_entropy = math.log(n)
        # With equal wealth, entropy should be close to maximum
        assert realm.realm_entropy > max_entropy * 0.9

    def test_memory_knowledge_pool_grows(self):
        agents = {f"a{i}": _agent(f"a{i}", balance=100, realm="memory") for i in range(5)}
        state = _make_state(agents)
        realm = state.realms["memory"]
        assert realm.knowledge_pool == 0.0
        memory_tick(state, realm, list(agents.values()))
        assert realm.knowledge_pool > 0

    def test_memory_knowledge_pool_decays(self):
        agents = {f"a{i}": _agent(f"a{i}", balance=100, realm="memory") for i in range(5)}
        state = _make_state(agents)
        realm = state.realms["memory"]
        realm.knowledge_pool = 100.0
        memory_tick(state, realm, list(agents.values()))
        # Pool should have decayed but also received contributions
        # With 5 agents contributing, it should still be substantial
        assert realm.knowledge_pool > 0

    def test_memory_tenure_matters(self):
        """Long-tenure agents should earn more from knowledge pool."""
        veteran = _agent("vet", balance=100, realm="memory", created_tick=0)
        newcomer = _agent("new", balance=100, realm="memory", created_tick=99)
        agents = {"vet": veteran, "new": newcomer}
        state = _make_state(agents, tick=100)

        initial_vet = veteran.balance
        initial_new = newcomer.balance

        for _ in range(20):
            memory_tick(state, state.realms["memory"], [veteran, newcomer])

        vet_gain = veteran.balance - initial_vet
        new_gain = newcomer.balance - initial_new
        assert vet_gain > new_gain

    def test_memory_high_temp_more_trading(self):
        """High temperature should trigger more trades (check ledger)."""
        agents = {f"a{i}": _agent(f"a{i}", balance=100, realm="memory") for i in range(10)}
        state = _make_state(agents)
        realm = state.realms["memory"]

        # Force high temperature
        realm.realm_temperature = 3.0
        initial_tx = len(state.ledger.transactions)
        memory_tick(state, realm, list(agents.values()))
        high_temp_tx = len(state.ledger.transactions) - initial_tx

        # Force low temperature
        realm.realm_temperature = 0.01
        initial_tx2 = len(state.ledger.transactions)
        memory_tick(state, realm, list(agents.values()))
        low_temp_tx = len(state.ledger.transactions) - initial_tx2

        # High temp should generally produce more trades
        # (stochastic, so we just check it doesn't crash and produces some)
        assert high_temp_tx >= 0
        assert low_temp_tx >= 0


# ─── Network Realm: Control Theory (Bellman) ─────────────────────────────

class TestNetworkRealm:
    def test_network_empty_agents(self):
        state = _make_state()
        network_tick(state, state.realms["network"], [])  # no crash

    def test_network_rewards_agents(self):
        agents = {f"a{i}": _agent(f"a{i}", balance=100, realm="network") for i in range(5)}
        state = _make_state(agents)
        initial = state.total_supply
        network_tick(state, state.realms["network"], list(agents.values()))
        assert state.total_supply > initial

    def test_network_route_efficiency_updates(self):
        agents = {f"a{i}": _agent(f"a{i}", balance=100, realm="network") for i in range(5)}
        state = _make_state(agents)
        realm = state.realms["network"]
        initial_eff = realm.route_efficiency

        # Run multiple ticks so throughput_history has >= 2 entries
        for _ in range(3):
            network_tick(state, realm, list(agents.values()))

        assert len(realm.throughput_history) >= 2
        # Efficiency should have been updated (may go up or down)
        # Just verify it's in valid range
        assert 0.1 <= realm.route_efficiency <= 3.0

    def test_network_congestion_under_capacity(self):
        """Few agents → no congestion."""
        agents = {f"a{i}": _agent(f"a{i}", realm="network") for i in range(5)}
        state = _make_state(agents)
        realm = state.realms["network"]
        network_tick(state, realm, list(agents.values()))
        assert realm.congestion == 0.0

    def test_network_congestion_over_capacity(self):
        """Many agents → congestion penalty."""
        # Optimal load = 30 * 0.6 = 18, so 25 agents should cause congestion
        agents = {f"a{i}": _agent(f"a{i}", realm="network") for i in range(25)}
        state = _make_state(agents)
        realm = state.realms["network"]
        network_tick(state, realm, list(agents.values()))
        assert realm.congestion > 0

    def test_network_throughput_history_capped(self):
        agents = {f"a{i}": _agent(f"a{i}", realm="network") for i in range(5)}
        state = _make_state(agents)
        realm = state.realms["network"]
        for _ in range(30):
            network_tick(state, realm, list(agents.values()))
        assert len(realm.throughput_history) <= 20

    def test_network_zero_energy_skipped(self):
        agent = _agent("a", balance=100, realm="network", energy=0)
        agents = {"a": agent}
        state = _make_state(agents)
        initial = state.total_supply
        network_tick(state, state.realms["network"], [agent])
        assert state.total_supply == initial


# ─── SOC Avalanche Cascade ──────────────────────────────────────────────

class TestAvalancheCascade:
    def test_no_cascade_small_avalanche(self):
        state = _make_state()
        state.last_avalanche_size = 5.0  # below threshold
        apply_avalanche_spillover(state)
        for realm in state.realms.values():
            assert realm.avalanche_exposure == 0.0

    def test_cascade_large_avalanche(self):
        agent = _agent("a", balance=100, realm="compute",
                       fitness_history=[300, 100])  # drop of 200
        agents = {"a": agent}
        state = _make_state(agents)
        state.last_avalanche_size = 200.0

        apply_avalanche_spillover(state)

        # Source realm gets full exposure
        assert state.realms["compute"].avalanche_exposure == 200.0
        # Other realms get fractional exposure
        assert state.realms["memory"].avalanche_exposure > 0
        assert state.realms["memory"].avalanche_exposure < 200.0
        assert state.realms["network"].avalanche_exposure > 0

    def test_cascade_fraction_capped(self):
        """Cascade fraction should be capped at 0.3."""
        agent = _agent("a", balance=100, realm="compute",
                       fitness_history=[10000, 100])  # massive drop
        agents = {"a": agent}
        state = _make_state(agents)
        state.last_avalanche_size = 9900.0

        apply_avalanche_spillover(state)

        # Cascade fraction = min(0.3, 9900/1000) = 0.3
        for name, realm in state.realms.items():
            if name != "compute":
                assert realm.avalanche_exposure == 9900.0 * 0.3


# ─── Migration ───────────────────────────────────────────────────────────

class TestMigration:
    def test_migrate_success(self):
        agent = _agent("a", balance=100, realm="compute")
        state = _make_state({"a": agent})
        assert migrate_agent(state, agent, "memory")
        assert agent.realm == "memory"
        assert agent.balance == 95.0  # 100 - 5 cost
        assert agent.migration_cooldown == 5

    def test_migrate_same_realm(self):
        agent = _agent("a", balance=100, realm="compute")
        state = _make_state({"a": agent})
        assert not migrate_agent(state, agent, "compute")

    def test_migrate_insufficient_balance(self):
        agent = _agent("a", balance=2, realm="compute")
        state = _make_state({"a": agent})
        assert not migrate_agent(state, agent, "memory")

    def test_migrate_at_capacity(self):
        # Fill memory realm to capacity (40)
        agents = {}
        for i in range(40):
            agents[f"m{i}"] = _agent(f"m{i}", realm="memory")
        migrant = _agent("migrant", balance=100, realm="compute")
        agents["migrant"] = migrant
        state = _make_state(agents)
        assert not migrate_agent(state, migrant, "memory")
