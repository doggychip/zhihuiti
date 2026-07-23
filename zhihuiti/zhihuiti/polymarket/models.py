"""Typed domain models for paper copy trading."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


ZERO = Decimal("0")


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class DecisionStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class SourceTrade:
    fingerprint: str
    wallet: str
    token_id: str
    condition_id: str
    side: Side
    size: Decimal
    price: Decimal
    timestamp: int
    transaction_hash: str
    outcome: str = ""
    title: str = ""
    occurrence: int = 0
    raw: dict[str, Any] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class BookLevel:
    price: Decimal
    size: Decimal


@dataclass(frozen=True)
class OrderBook:
    token_id: str
    condition_id: str
    timestamp_ms: int
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]
    book_hash: str = ""
    minimum_order_size: Decimal = ZERO
    tick_size: Decimal = Decimal("0.01")


@dataclass(frozen=True)
class FeeSchedule:
    rate: Decimal = ZERO
    exponent: Decimal = Decimal("1")
    taker_only: bool = True

    def fee(self, shares: Decimal, price: Decimal) -> Decimal:
        """Return the current V2 taker fee for one execution level."""
        if self.rate <= ZERO or shares <= ZERO:
            return ZERO
        return shares * self.rate * (price * (Decimal("1") - price)) ** self.exponent


@dataclass(frozen=True)
class MarketMetadata:
    condition_id: str
    tokens: dict[str, str]
    active: bool = True
    closed: bool = False
    accepting_orders: bool = True
    winners: frozenset[str] = frozenset()
    fee: FeeSchedule = FeeSchedule()

    @property
    def resolved(self) -> bool:
        return self.closed and bool(self.winners)


@dataclass(frozen=True)
class CopyDecision:
    source_fingerprint: str
    status: DecisionStatus
    reason: str
    requested_size: Decimal
    approved_size: Decimal = ZERO
    arrival_timestamp_ms: int = 0


@dataclass(frozen=True)
class FillLevel:
    price: Decimal
    size: Decimal
    fee: Decimal


@dataclass(frozen=True)
class SimulatedFill:
    source_fingerprint: str
    side: Side
    token_id: str
    condition_id: str
    requested_size: Decimal
    filled_size: Decimal
    average_price: Decimal
    notional: Decimal
    fee: Decimal
    book_timestamp_ms: int
    book_hash: str
    levels: tuple[FillLevel, ...] = ()

    @property
    def partial(self) -> bool:
        return ZERO < self.filled_size < self.requested_size


@dataclass(frozen=True)
class Position:
    token_id: str
    condition_id: str
    shares: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal


@dataclass(frozen=True)
class PortfolioSnapshot:
    cash: Decimal
    positions: tuple[Position, ...]
    realized_pnl: Decimal
    unrealized_pnl: Decimal = ZERO
