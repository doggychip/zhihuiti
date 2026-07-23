"""Pure deterministic copy sizing and risk controls."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from zhihuiti.polymarket.config import PolymarketConfig
from zhihuiti.polymarket.models import (
    CopyDecision,
    DecisionStatus,
    Side,
    SourceTrade,
    ZERO,
)


class DeterministicCopyEngine:
    def __init__(self, config: PolymarketConfig) -> None:
        self.config = config

    def decide(
        self,
        trade: SourceTrade,
        *,
        now_timestamp: int,
        cash: Decimal,
        inventory: Decimal,
        market_exposure: Decimal,
    ) -> CopyDecision:
        requested = (trade.size * self.config.copy_ratio).quantize(
            Decimal("0.000001"), rounding=ROUND_DOWN
        )
        # The follower can only react after this polling observation, not at
        # the leader's historical execution timestamp.
        arrival = now_timestamp * 1000 + self.config.simulated_latency_ms

        def reject(reason: str) -> CopyDecision:
            return CopyDecision(
                source_fingerprint=trade.fingerprint,
                status=DecisionStatus.REJECTED,
                reason=reason,
                requested_size=requested,
                arrival_timestamp_ms=arrival,
            )

        if requested <= ZERO:
            return reject("copy_size_below_precision")
        if now_timestamp - trade.timestamp > self.config.stale_after_seconds:
            return reject("stale_source_trade")

        approved = requested
        if trade.side is Side.BUY:
            worst_price = min(
                Decimal("1"), trade.price * (Decimal("1") + self.config.max_slippage)
            )
            approved = min(approved, cash / worst_price if worst_price else ZERO)
            remaining_market = self.config.max_market_exposure - market_exposure
            approved = min(
                approved,
                max(ZERO, remaining_market) / worst_price if worst_price else ZERO,
            )
        else:
            approved = min(approved, inventory)

        approved = min(approved, self.config.max_trade_notional / trade.price)
        approved = approved.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        if approved <= ZERO:
            if trade.side is Side.SELL and inventory <= ZERO:
                return reject("insufficient_inventory")
            if trade.side is Side.BUY and cash <= ZERO:
                return reject("insufficient_cash")
            if trade.side is Side.BUY and market_exposure >= self.config.max_market_exposure:
                return reject("market_exposure_cap")
            return reject("trade_notional_cap")

        reason = "accepted"
        if approved < requested:
            if trade.side is Side.SELL and approved == inventory:
                reason = "accepted_inventory_limited"
            elif approved * trade.price >= self.config.max_trade_notional:
                reason = "accepted_trade_cap_limited"
            elif trade.side is Side.BUY and approved * trade.price >= (
                self.config.max_market_exposure - market_exposure
            ):
                reason = "accepted_market_cap_limited"
            else:
                reason = "accepted_cash_limited"
        return CopyDecision(
            source_fingerprint=trade.fingerprint,
            status=DecisionStatus.ACCEPTED,
            reason=reason,
            requested_size=requested,
            approved_size=approved,
            arrival_timestamp_ms=arrival,
        )
