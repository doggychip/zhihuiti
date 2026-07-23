"""Public, unauthenticated Polymarket HTTP clients."""

from __future__ import annotations

import json
import time
from decimal import Decimal
from typing import Any, Callable

import httpx

from zhihuiti.polymarket.models import (
    BookLevel,
    FeeSchedule,
    MarketMetadata,
    OrderBook,
)


def parse_book_payload(data: dict[str, Any], token_id: str = "") -> OrderBook:
    def levels(name: str) -> tuple[BookLevel, ...]:
        raw_levels = data.get(name) or ()
        return tuple(
            BookLevel(price=Decimal(str(level["price"])), size=Decimal(str(level["size"])))
            for level in raw_levels
        )

    return OrderBook(
        token_id=str(data.get("asset_id", token_id)),
        condition_id=str(data.get("market", "")),
        timestamp_ms=int(data.get("timestamp", 0)),
        bids=levels("bids"),
        asks=levels("asks"),
        book_hash=str(data.get("hash", "")),
        minimum_order_size=Decimal(str(data.get("min_order_size", "0"))),
        tick_size=Decimal(str(data.get("tick_size", "0.01"))),
    )


def parse_market_payload(data: dict[str, Any], condition_id: str = "") -> MarketMetadata:
    tokens: dict[str, str] = {}
    winners: set[str] = set()
    for item in data.get("t", data.get("tokens", [])) or []:
        token_id = str(item.get("t", item.get("token_id", "")))
        if not token_id:
            continue
        tokens[token_id] = str(item.get("o", item.get("outcome", "")))
        if item.get("winner") is True:
            winners.add(token_id)
    fee_data = data.get("fd") or {}
    fee = FeeSchedule(
        rate=Decimal(str(fee_data.get("r", "0"))),
        exponent=Decimal(str(fee_data.get("e", "1"))),
        taker_only=bool(fee_data.get("to", True)),
    )
    closed = bool(data.get("closed", data.get("c", False)))
    accepting = bool(data.get("accepting_orders", data.get("ao", not closed)))
    return MarketMetadata(
        condition_id=str(data.get("condition_id", data.get("conditionId", condition_id))),
        tokens=tokens,
        active=bool(data.get("active", True)),
        closed=closed,
        accepting_orders=accepting,
        winners=frozenset(winners),
        fee=fee,
    )


def _payload(response: httpx.Response) -> Any:
    """Decode JSON numbers directly to Decimal when response text is available."""
    text = getattr(response, "text", None)
    if isinstance(text, str) and text:
        return json.loads(text, parse_float=Decimal)
    return response.json()


class PolymarketClient:
    """Retrying client for the public Data API and CLOB."""

    def __init__(
        self,
        data_api_url: str = "https://data-api.polymarket.com",
        clob_api_url: str = "https://clob.polymarket.com",
        timeout: float = 15,
        retries: int = 3,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.data_api_url = data_api_url.rstrip("/")
        self.clob_api_url = clob_api_url.rstrip("/")
        self.retries = retries
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None
        self._sleep = sleep

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> PolymarketClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return _payload(response)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                retryable = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code >= 500
                if attempt >= self.retries or not retryable:
                    raise
                self._sleep(0.25 * (2**attempt))
        raise RuntimeError("request retry loop exhausted") from last_error

    def fetch_trades(
        self,
        wallet: str,
        *,
        start: int | None = None,
        end: int | None = None,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch all available pages for a wallet, including maker observations."""
        trades: list[dict[str, Any]] = []
        offset = 0
        while offset <= 10000:
            params: dict[str, str | int] = {
                "user": wallet,
                "takerOnly": "false",
                "limit": page_size,
                "offset": offset,
            }
            if start is not None:
                params["start"] = start
            if end is not None:
                params["end"] = end
            page = self._request("GET", f"{self.data_api_url}/trades", params=params)
            if not isinstance(page, list):
                raise ValueError("Data API trades response must be a list")
            trades.extend(item for item in page if isinstance(item, dict))
            if len(page) < page_size:
                break
            offset += page_size
        return trades

    def fetch_book(self, token_id: str) -> OrderBook:
        data = self._request(
            "GET",
            f"{self.clob_api_url}/book",
            params={"token_id": token_id},
        )
        if not isinstance(data, dict):
            raise ValueError("CLOB book response must be an object")
        return parse_book_payload(data, token_id)

    def fetch_market(self, condition_id: str) -> MarketMetadata:
        data = self._request("GET", f"{self.clob_api_url}/clob-markets/{condition_id}")
        if not isinstance(data, dict):
            raise ValueError("CLOB market response must be an object")
        return parse_market_payload(data, condition_id)
