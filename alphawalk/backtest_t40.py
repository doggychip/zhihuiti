#!/usr/bin/env python3
"""Point-in-time evaluator for T40's deterministic recommendation rule.

Input CSV columns: date,symbol,close. The file must contain SPY, QQQ, IWM and
the requested watchlist. Signals use only rows dated on or before each signal
date. Forward returns are attached afterward solely for evaluation.
"""
import argparse
import csv
import datetime
import json
from collections import defaultdict


def ema(values, period):
    if not values:
        return []
    k = 2.0 / (period + 1.0)
    out = [values[0]]
    for value in values[1:]:
        out.append(value * k + out[-1] * (1.0 - k))
    return out


def pct(values, bars):
    if len(values) <= bars or values[-1-bars] == 0:
        return None
    return (values[-1] / values[-1-bars] - 1.0) * 100.0


def load_prices(path):
    by_symbol = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                day = datetime.date.fromisoformat(row["date"])
                symbol = row["symbol"].strip().upper()
                close = float(row["close"])
            except (KeyError, TypeError, ValueError):
                continue
            if symbol and close > 0:
                by_symbol[symbol][day] = close
    return dict(by_symbol)


def series_through(prices, symbol, day):
    rows = sorted((date, close) for date, close in prices.get(symbol, {}).items() if date <= day)
    return [date for date, _ in rows], [close for _, close in rows]


def forward_return(prices, symbol, day, sessions):
    rows = sorted((date, close) for date, close in prices.get(symbol, {}).items() if date >= day)
    if not rows or rows[0][0] != day or len(rows) <= sessions or rows[0][1] == 0:
        return None
    return (rows[sessions][1] / rows[0][1] - 1.0) * 100.0


def regime_on(prices, day):
    rows = []
    for symbol in ("SPY", "QQQ", "IWM"):
        _, values = series_through(prices, symbol, day)
        if len(values) < 22:
            continue
        e21 = ema(values, 21)[-1]
        rows.append((values[-1] > e21, pct(values, 5)))
    if len(rows) < 2:
        return "unavailable"
    positive = sum(1 for above, change in rows if above and (change or 0) > 0)
    negative = sum(1 for above, change in rows if not above and (change or 0) < 0)
    return "constructive" if positive >= 2 else "defensive" if negative >= 2 else "mixed"


def candidates_on(prices, watchlist, day, regime):
    candidates = []
    if regime not in ("constructive", "defensive"):
        return candidates
    for symbol in watchlist:
        _, values = series_through(prices, symbol, day)
        if len(values) < 31:
            continue
        e21s = ema(values, 21)
        e21 = e21s[-1]
        distance = (values[-1] / e21 - 1.0) * 100.0 if e21 else None
        slope = (e21 / e21s[-11] - 1.0) * 100.0 if e21s[-11] else None
        d5, d20 = pct(values, 5), pct(values, 20)
        if None in (distance, slope, d5, d20):
            continue
        if regime == "constructive" and values[-1] > e21 and d5 > 0:
            if slope > 0 and d20 > 0 and 0 < distance <= 5.0:
                candidates.append((abs(distance), symbol, "Buy"))
        elif regime == "defensive" and values[-1] < e21 and d5 < 0:
            if slope < 0 and d20 < 0 and -5.0 <= distance < 0:
                candidates.append((abs(distance), symbol, "Sell"))
    return sorted(candidates)[:3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prices_csv")
    parser.add_argument("--watchlist", required=True, help="Comma-separated point-in-time universe")
    parser.add_argument("--cost-bps", type=float, default=10.0,
                        help="Round-trip cost deducted from each evaluated event")
    parser.add_argument("--events-out", help="Optional JSON file for event-level results")
    args = parser.parse_args()
    prices = load_prices(args.prices_csv)
    watchlist = list(dict.fromkeys(
        symbol.strip().upper() for symbol in args.watchlist.split(",") if symbol.strip()))
    dates = sorted(set(prices.get("SPY", {})) & set(prices.get("QQQ", {}))
                   & set(prices.get("IWM", {})))
    events = []
    for day in dates:
        regime = regime_on(prices, day)
        for _, symbol, action in candidates_on(prices, watchlist, day, regime):
            event = {"date": day.isoformat(), "symbol": symbol, "action": action,
                     "regime": regime, "rule_version": "t40-structure-v1"}
            sign = 1.0 if action == "Buy" else -1.0
            for horizon in (1, 5, 20):
                raw = forward_return(prices, symbol, day, horizon)
                benchmark = forward_return(prices, "SPY", day, horizon)
                key = "excess_%dd_net_pct" % horizon
                event[key] = (round(sign * (raw-benchmark) - args.cost_bps/100.0, 4)
                              if raw is not None and benchmark is not None else None)
            events.append(event)
    summary = {
        "schema_version": "1.0.0",
        "rule_version": "t40-structure-v1",
        "input": args.prices_csv,
        "watchlist": watchlist,
        "cost_bps": args.cost_bps,
        "events": len(events),
        "metrics": {},
        "caveats": [
            "The supplied watchlist must be point-in-time; a current-only universe creates survivorship bias.",
            "Corporate actions and delistings must already be reflected correctly in input closes.",
            "This evaluator measures a fixed rule; it does not establish future profitability.",
        ],
    }
    for horizon in (1, 5, 20):
        values = [event["excess_%dd_net_pct" % horizon] for event in events
                  if event["excess_%dd_net_pct" % horizon] is not None]
        summary["metrics"]["%dd" % horizon] = {
            "n": len(values),
            "mean_excess_net_pct": round(sum(values)/len(values), 4) if values else None,
            "positive_share": round(sum(value > 0 for value in values)/len(values), 4)
                              if values else None,
            "worst_excess_net_pct": min(values) if values else None,
        }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.events_out:
        with open(args.events_out, "w", encoding="utf-8") as handle:
            json.dump(events, handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
