"""Market data fetchers — equities, forex, and indices via Yahoo Finance.

No API key required. Uses Yahoo Finance v8 chart API.
Returns OHLCV candles in the same format as crypto fetcher.
"""

from __future__ import annotations

DEFAULT_EQUITIES = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "JPM", "V", "WMT",
]

DEFAULT_FOREX = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
    "USDCHF=X", "NZDUSD=X", "EURGBP=X",
]

DEFAULT_INDICES = [
    "^GSPC", "^DJI", "^IXIC", "^RUT",  # US
    "^FTSE", "^GDAXI", "^N225", "^HSI",  # International
]

# Yahoo interval map: our timeframe → Yahoo interval + range
_YAHOO_PARAMS = {
    "1h": ("1h", "7d"),
    "4h": ("1h", "30d"),   # Yahoo doesn't have 4h; fetch 1h and downsample
    "1d": ("1d", "6mo"),
    "1w": ("1wk", "2y"),
}


def fetch_yahoo_candles(symbol: str, timeframe: str = "1d") -> list[dict]:
    """Fetch OHLCV candles from Yahoo Finance.

    Args:
        symbol: Yahoo Finance symbol (e.g. AAPL, EURUSD=X, ^GSPC)
        timeframe: One of 1h, 4h, 1d, 1w

    Returns:
        List of {open, high, low, close, volume} dicts.
    """
    try:
        import httpx

        interval, rnge = _YAHOO_PARAMS.get(timeframe, ("1d", "6mo"))

        resp = httpx.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": interval, "range": rnge},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        result = data.get("chart", {}).get("result", [])
        if not result:
            return []

        quote = result[0].get("indicators", {}).get("quote", [{}])[0]
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])

        candles = []
        for i in range(len(closes)):
            if closes[i] is None:
                continue
            candles.append({
                "open": opens[i] or closes[i],
                "high": highs[i] or closes[i],
                "low": lows[i] or closes[i],
                "close": closes[i],
                "volume": volumes[i] or 0,
            })

        # Downsample 1h → 4h if needed
        if timeframe == "4h" and interval == "1h" and len(candles) > 4:
            candles = _downsample(candles, 4)

        return candles
    except Exception:
        return []


def _downsample(candles: list[dict], factor: int) -> list[dict]:
    """Downsample candles by grouping `factor` candles into one."""
    result = []
    for i in range(0, len(candles) - factor + 1, factor):
        group = candles[i:i + factor]
        result.append({
            "open": group[0]["open"],
            "high": max(c["high"] for c in group),
            "low": min(c["low"] for c in group),
            "close": group[-1]["close"],
            "volume": sum(c["volume"] for c in group),
        })
    return result


def scan_equities(
    symbols: list[str] | None = None,
    timeframe: str = "1d",
) -> list:
    """Scan equities using the universal oracle.

    Returns list of ScanResult-compatible dicts.
    """
    from zhihuiti.scanner import ScanResult, _compute_signal_score
    from zhihuiti.crypto_oracle import diagnose_market

    if symbols is None:
        symbols = DEFAULT_EQUITIES

    results = []
    for sym in symbols:
        try:
            candles = fetch_yahoo_candles(sym, timeframe)
            if not candles or len(candles) < 10:
                continue

            diag = diagnose_market(candles, instrument=sym)
            signal_score = _compute_signal_score(diag)
            top_pattern = diag.patterns[0] if diag.patterns else None

            results.append(ScanResult(
                instrument=sym,
                price=diag.price,
                change_pct=diag.change_pct,
                regime=diag.regime,
                dominant_theory=diag.dominant_theory,
                pattern_count=len(diag.patterns),
                top_pattern=top_pattern.name if top_pattern else "",
                top_pattern_strength=top_pattern.strength if top_pattern else 0.0,
                collision_count=len(diag.collision_insights),
                signal_score=signal_score,
            ))
        except Exception:
            continue

    results.sort(key=lambda r: -r.signal_score)
    return results


def scan_forex(
    symbols: list[str] | None = None,
    timeframe: str = "1d",
) -> list:
    """Scan forex pairs."""
    if symbols is None:
        symbols = DEFAULT_FOREX
    return scan_equities(symbols=symbols, timeframe=timeframe)


def scan_indices(
    symbols: list[str] | None = None,
    timeframe: str = "1d",
) -> list:
    """Scan market indices."""
    if symbols is None:
        symbols = DEFAULT_INDICES
    return scan_equities(symbols=symbols, timeframe=timeframe)
