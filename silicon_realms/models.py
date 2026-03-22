from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Agent:
    id: str
    name: str
    realm: str
    balance: float = 0.0
    staked: float = 0.0
    strategy: str = "balanced"
    energy: int = 100
    created_tick: int = 0
    migration_cooldown: int = 0
    fitness_history: list = field(default_factory=list)  # for replicator dynamics


@dataclass
class Transaction:
    tick: int
    sender: str
    receiver: str
    amount: float
    tx_type: str  # mint, transfer, stake, unstake, reward, fee


@dataclass
class Realm:
    name: str
    capacity: int
    base_reward: float
    params: dict = field(default_factory=dict)

    # ── Per-realm theoretical state ──────────────────────────────────────
    # Compute realm: replicator dynamics
    selection_pressure: float = 1.0           # amplifies fitness gap → strategy evolution
    dominant_strategy: str = ""               # current fittest strategy in this realm
    strategy_fitness: dict = field(default_factory=dict)  # strategy → mean fitness

    # Memory realm: statistical mechanics
    realm_temperature: float = 1.0            # local knowledge disorder
    realm_entropy: float = 0.0                # local Shannon entropy of wealth
    knowledge_pool: float = 0.0               # shared knowledge reservoir

    # Network realm: control theory (Bellman)
    route_efficiency: float = 1.0             # learned routing quality [0,1]→reward multiplier
    congestion: float = 0.0                   # excess agents above optimal → penalty
    throughput_history: list = field(default_factory=list)  # for TD learning

    # SOC: cross-realm avalanche state
    avalanche_exposure: float = 0.0           # realm-local cascade severity this tick


@dataclass
class Ledger:
    transactions: list[Transaction] = field(default_factory=list)

    def record(self, tick: int, sender: str, receiver: str, amount: float, tx_type: str):
        self.transactions.append(Transaction(tick, sender, receiver, amount, tx_type))


@dataclass
class SimState:
    tick: int = 0
    realms: dict[str, Realm] = field(default_factory=dict)
    agents: dict[str, Agent] = field(default_factory=dict)
    ledger: Ledger = field(default_factory=Ledger)
    total_supply: float = 0.0
    rng: random.Random = field(default_factory=lambda: random.Random(42))
    config: dict = field(default_factory=dict)
    # Statistical mechanics
    temperature: float = 1.0        # economic temperature (controls wealth spread)
    entropy: float = 0.0            # Shannon entropy of wealth distribution
    # Control theory
    realm_values: dict = field(default_factory=dict)   # Bellman value per realm
    # SOC
    last_avalanche_size: float = 0.0  # largest wealth drop this tick
