"""Configuration for the paper-only Polymarket subsystem."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping


def _decimal(value: str, name: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _wallets(value: str) -> tuple[str, ...]:
    wallets = tuple(item.strip().lower() for item in value.split(",") if item.strip())
    for wallet in wallets:
        if len(wallet) != 42 or not wallet.startswith("0x"):
            raise ValueError(f"invalid wallet address: {wallet}")
        try:
            int(wallet[2:], 16)
        except ValueError as exc:
            raise ValueError(f"invalid wallet address: {wallet}") from exc
    if len(set(wallets)) != len(wallets):
        raise ValueError("leader wallets must be unique")
    return wallets


@dataclass(frozen=True)
class PolymarketConfig:
    """Validated settings; there are deliberately no keys or live-order flags."""

    leader_wallets: tuple[str, ...]
    database_path: Path = Path("polymarket-paper.db")
    starting_cash: Decimal = Decimal("10000")
    copy_ratio: Decimal = Decimal("0.10")
    polling_interval_seconds: Decimal = Decimal("10")
    polling_overlap_seconds: int = 30
    simulated_latency_ms: int = 1000
    max_slippage: Decimal = Decimal("0.03")
    max_trade_notional: Decimal = Decimal("250")
    max_market_exposure: Decimal = Decimal("1000")
    stale_after_seconds: int = 60
    page_size: int = 500
    request_timeout_seconds: Decimal = Decimal("15")
    request_retries: int = 3
    data_api_url: str = "https://data-api.polymarket.com"
    clob_api_url: str = "https://clob.polymarket.com"

    def __post_init__(self) -> None:
        normalized_wallets = _wallets(",".join(self.leader_wallets))
        object.__setattr__(self, "leader_wallets", normalized_wallets)
        if self.starting_cash < 0:
            raise ValueError("starting_cash cannot be negative")
        for name in ("copy_ratio", "polling_interval_seconds", "max_trade_notional", "max_market_exposure"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if not ZERO <= self.max_slippage <= Decimal("1"):
            raise ValueError("max_slippage must be between 0 and 1")
        for name in ("polling_overlap_seconds", "simulated_latency_ms", "stale_after_seconds"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")
        if not 1 <= self.page_size <= 10000:
            raise ValueError("page_size must be between 1 and 10000")
        if self.request_retries < 0:
            raise ValueError("request_retries cannot be negative")

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        **overrides: object,
    ) -> PolymarketConfig:
        env = os.environ if environ is None else environ
        values: dict[str, object] = {
            "leader_wallets": _wallets(env.get("POLYMARKET_LEADER_WALLETS", "")),
            "database_path": Path(env.get("POLYMARKET_DB", "polymarket-paper.db")),
            "starting_cash": _decimal(env.get("POLYMARKET_STARTING_CASH", "10000"), "starting cash"),
            "copy_ratio": _decimal(env.get("POLYMARKET_COPY_RATIO", "0.10"), "copy ratio"),
            "polling_interval_seconds": _decimal(env.get("POLYMARKET_POLL_INTERVAL", "10"), "poll interval"),
            "polling_overlap_seconds": int(env.get("POLYMARKET_POLL_OVERLAP", "30")),
            "simulated_latency_ms": int(env.get("POLYMARKET_SIMULATED_LATENCY_MS", "1000")),
            "max_slippage": _decimal(env.get("POLYMARKET_MAX_SLIPPAGE", "0.03"), "max slippage"),
            "max_trade_notional": _decimal(env.get("POLYMARKET_MAX_TRADE_NOTIONAL", "250"), "trade cap"),
            "max_market_exposure": _decimal(env.get("POLYMARKET_MAX_MARKET_EXPOSURE", "1000"), "market cap"),
            "stale_after_seconds": int(env.get("POLYMARKET_STALE_AFTER", "60")),
            "page_size": int(env.get("POLYMARKET_PAGE_SIZE", "500")),
            "request_timeout_seconds": _decimal(env.get("POLYMARKET_TIMEOUT", "15"), "timeout"),
            "request_retries": int(env.get("POLYMARKET_RETRIES", "3")),
            "data_api_url": env.get("POLYMARKET_DATA_API_URL", "https://data-api.polymarket.com"),
            "clob_api_url": env.get("POLYMARKET_CLOB_API_URL", "https://clob.polymarket.com"),
        }
        values.update({key: value for key, value in overrides.items() if value is not None})
        if isinstance(values["leader_wallets"], str):
            values["leader_wallets"] = _wallets(values["leader_wallets"])
        if isinstance(values["database_path"], str):
            values["database_path"] = Path(values["database_path"])
        return cls(**values)  # type: ignore[arg-type]


ZERO = Decimal("0")
