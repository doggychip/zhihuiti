"""Typed domain models for paper copy trading."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
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

    def __post_init__(self) -> None:
        if (
            not self.rate.is_finite()
            or not self.exponent.is_finite()
            or self.rate < ZERO
            or self.exponent < ZERO
        ):
            raise ValueError("fee rate and exponent must be finite and non-negative")

    def fee(self, shares: Decimal, price: Decimal) -> Decimal:
        """Return the current V2 taker fee for one execution level."""
        if not price.is_finite() or not ZERO <= price <= Decimal("1"):
            raise ValueError("fee price must be between 0 and 1")
        if self.rate <= ZERO or shares <= ZERO:
            return ZERO
        raw = shares * self.rate * (
            price * (Decimal("1") - price)
        ) ** self.exponent
        precision = Decimal("0.00001")
        if raw < precision:
            return ZERO
        return raw.quantize(precision, rounding=ROUND_HALF_UP)


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

    @property
    def position_size(self) -> Decimal:
        """Net outcome shares received or removed after protocol fees."""
        if self.side is Side.SELL:
            return self.filled_size
        fee_shares = sum(
            (
                level.fee / level.price
                for level in self.levels
                if level.price > ZERO
            ),
            ZERO,
        )
        # Manually constructed fills may not carry level detail.
        if not self.levels and self.average_price > ZERO:
            fee_shares = self.fee / self.average_price
        return max(ZERO, self.filled_size - fee_shares)


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
