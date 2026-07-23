"""Conservative immediate-fill simulation against a public book snapshot."""

from __future__ import annotations

from decimal import Decimal

from zhihuiti.polymarket.models import (
    FeeSchedule,
    FillLevel,
    OrderBook,
    Side,
    SimulatedFill,
    SourceTrade,
    ZERO,
)


class OrderBookFillSimulator:
    def simulate(
        self,
        trade: SourceTrade,
        requested_size: Decimal,
        book: OrderBook,
        *,
        max_slippage: Decimal,
        fee_schedule: FeeSchedule = FeeSchedule(),
    ) -> SimulatedFill:
        if book.token_id != trade.token_id:
            raise ValueError("book token does not match source trade")
        if requested_size <= ZERO:
            raise ValueError("requested size must be positive")
        if book.minimum_order_size and requested_size < book.minimum_order_size:
            return self._empty(trade, requested_size, book)

        if trade.side is Side.BUY:
            levels = sorted(book.asks, key=lambda level: level.price)
            boundary = min(Decimal("1"), trade.price * (Decimal("1") + max_slippage))
            executable = lambda price: price <= boundary
        else:
            levels = sorted(book.bids, key=lambda level: level.price, reverse=True)
            boundary = max(ZERO, trade.price * (Decimal("1") - max_slippage))
            executable = lambda price: price >= boundary

        remaining = requested_size
        fills: list[FillLevel] = []
        for level in levels:
            if remaining <= ZERO or level.size <= ZERO:
                continue
            if not executable(level.price):
                break
            size = min(remaining, level.size)
            fee = fee_schedule.fee(size, level.price)
            fills.append(FillLevel(price=level.price, size=size, fee=fee))
            remaining -= size

        filled = sum((level.size for level in fills), ZERO)
        notional = sum((level.size * level.price for level in fills), ZERO)
        fee = sum((level.fee for level in fills), ZERO)
        average = notional / filled if filled else ZERO
        return SimulatedFill(
            source_fingerprint=trade.fingerprint,
            side=trade.side,
            token_id=trade.token_id,
            condition_id=trade.condition_id,
            requested_size=requested_size,
            filled_size=filled,
            average_price=average,
            notional=notional,
            fee=fee,
            book_timestamp_ms=book.timestamp_ms,
            book_hash=book.book_hash,
            levels=tuple(fills),
        )

    @staticmethod
    def _empty(
        trade: SourceTrade,
        requested_size: Decimal,
        book: OrderBook,
    ) -> SimulatedFill:
        return SimulatedFill(
            source_fingerprint=trade.fingerprint,
            side=trade.side,
            token_id=trade.token_id,
            condition_id=trade.condition_id,
            requested_size=requested_size,
            filled_size=ZERO,
            average_price=ZERO,
            notional=ZERO,
            fee=ZERO,
            book_timestamp_ms=book.timestamp_ms,
            book_hash=book.book_hash,
        )
