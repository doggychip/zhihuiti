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
