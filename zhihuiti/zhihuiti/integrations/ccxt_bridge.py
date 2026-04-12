"""CCXT Bridge — unified exchange API for live trading.

Wraps ccxt (100+ exchanges) for zhihuiti trading agents.
Supports fetching OHLCV, tickers, order books, placing orders,
and querying balances across any ccxt-supported exchange.

Install: pip install ccxt
If ccxt is not installed, all methods gracefully return empty results.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class CCXTBridge:
    """Bridge to ccxt for unified exchange connectivity.

    Lazy-initializes the exchange on first use. If ccxt is not installed,
    is_available() returns False and all data methods return empty results.
    """

    def __init__(self, exchange_id: str = "binance", config: dict | None = None):
        self._exchange_id = exchange_id
        self._config = config or {}
        self._exchange: Any = None
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if ccxt is installed and the exchange can be initialized."""
        if self._available is not None:
            return self._available

        try:
            import ccxt  # noqa: F401
            self._available = True
        except ImportError:
            logger.debug("ccxt not installed — CCXTBridge disabled")
            self._available = False

        return self._available

    def _get_exchange(self) -> Any:
        """Lazy-init the exchange instance."""
        if self._exchange is not None:
            return self._exchange

        if not self.is_available():
            return None

        try:
            import ccxt

            exchange_class = getattr(ccxt, self._exchange_id, None)
            if exchange_class is None:
                logger.error("Unknown exchange: %s", self._exchange_id)
                self._available = False
                return None

            self._exchange = exchange_class(self._config)
            self._exchange.load_markets()
            return self._exchange
        except Exception as e:
            logger.error("Failed to initialize exchange %s: %s", self._exchange_id, e)
            self._available = False
            return None

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1d", limit: int = 100
    ) -> list[dict]:
        """Fetch OHLCV candles in zhihuiti format.

        Returns list of dicts with keys: timestamp, open, high, low, close, volume.
        Returns empty list if ccxt is unavailable or the call fails.
        """
        exchange = self._get_exchange()
        if exchange is None:
            return []

        try:
            raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return [
                {
                    "timestamp": datetime.fromtimestamp(
                        candle[0] / 1000, tz=timezone.utc
                    ).isoformat(),
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5],
                }
                for candle in raw
            ]
        except Exception as e:
            logger.error("fetch_ohlcv(%s) failed: %s", symbol, e)
            return []

    def fetch_ticker(self, symbol: str) -> dict:
        """Fetch current ticker for a symbol.

        Returns dict with last, bid, ask, volume, etc. Empty dict on failure.
        """
        exchange = self._get_exchange()
        if exchange is None:
            return {}

        try:
            ticker = exchange.fetch_ticker(symbol)
            return {
                "symbol": ticker.get("symbol", symbol),
                "last": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "timestamp": ticker.get("datetime"),
            }
        except Exception as e:
            logger.error("fetch_ticker(%s) failed: %s", symbol, e)
            return {}

    def fetch_order_book(self, symbol: str, limit: int = 20) -> dict:
        """Fetch order book (bids and asks).

        Returns dict with 'bids' and 'asks' lists. Empty dict on failure.
        """
        exchange = self._get_exchange()
        if exchange is None:
            return {}

        try:
            book = exchange.fetch_order_book(symbol, limit=limit)
            return {
                "symbol": symbol,
                "bids": [{"price": b[0], "amount": b[1]} for b in book.get("bids", [])],
                "asks": [{"price": a[0], "amount": a[1]} for a in book.get("asks", [])],
                "timestamp": book.get("datetime"),
            }
        except Exception as e:
            logger.error("fetch_order_book(%s) failed: %s", symbol, e)
            return {}

    def create_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float | None = None,
        order_type: str = "limit",
    ) -> dict:
        """Place an order on the exchange.

        Args:
            symbol: Trading pair (e.g. "BTC/USDT").
            side: "buy" or "sell".
            amount: Order quantity.
            price: Limit price. Required for limit orders, ignored for market.
            order_type: "limit" or "market".

        Returns order info dict. Empty dict on failure.
        """
        exchange = self._get_exchange()
        if exchange is None:
            return {}

        try:
            order = exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
            )
            return {
                "id": order.get("id"),
                "symbol": order.get("symbol"),
                "side": order.get("side"),
                "type": order.get("type"),
                "amount": order.get("amount"),
                "price": order.get("price"),
                "status": order.get("status"),
                "timestamp": order.get("datetime"),
            }
        except Exception as e:
            logger.error("create_order(%s %s %s) failed: %s", side, amount, symbol, e)
            return {}

    def fetch_balance(self) -> dict:
        """Fetch account balances.

        Returns dict mapping currency to {free, used, total}. Empty dict on failure.
        """
        exchange = self._get_exchange()
        if exchange is None:
            return {}

        try:
            balance = exchange.fetch_balance()
            # Filter to non-zero balances for readability
            result = {}
            for currency, amounts in balance.get("total", {}).items():
                if amounts and amounts > 0:
                    result[currency] = {
                        "free": balance.get("free", {}).get(currency, 0),
                        "used": balance.get("used", {}).get(currency, 0),
                        "total": amounts,
                    }
            return result
        except Exception as e:
            logger.error("fetch_balance failed: %s", e)
            return {}

    @staticmethod
    def list_exchanges() -> list[str]:
        """List all supported exchange IDs.

        Returns empty list if ccxt is not installed.
        """
        try:
            import ccxt
            return ccxt.exchanges
        except ImportError:
            return []


# Singleton for lazy initialization
_bridge: CCXTBridge | None = None


def get_bridge(exchange_id: str = "binance", config: dict | None = None) -> CCXTBridge:
    """Get or create the global CCXT bridge instance.

    Note: if called with different exchange_id after first init, returns
    the original instance. Create a new CCXTBridge directly for multi-exchange use.
    """
    global _bridge
    if _bridge is None:
        _bridge = CCXTBridge(exchange_id=exchange_id, config=config)
    return _bridge
