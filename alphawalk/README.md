# AlphaWalk Morning Command Center

`T40 - AlphaWalk Morning Command Center` is a standalone XTrader workflow for a
weekday US-equity morning brief.

## What it does

- Fetches compact daily histories for SPY, QQQ, IWM, TLT, GLD, and USO.
- Screens the first six valid watchlist symbols for 21-day structure and change.
- Collects dated overnight developments and today's market calendar.
- Labels portfolio holdings without changing the analytical rules.
- Computes market regime, watchlist classifications, source health, and the
  monitor queue in deterministic Python before narration.
- Emits deterministic Tier-B Buy/Sell screening leads when the market and
  complete publication contract is verified and directionally aligned. Leads
  are capped at three, never use Strong, and can be disabled with a workflow toggle.
- Validates issuer identity, source dates, time zone, market session, freshness,
  and minimum watchlist coverage before conclusions are publishable.
- Resolves the expected completed NYSE session across weekends and US market
  holidays, and requires Yahoo/Finnhub identity concordance.
- Assigns `verified`, `partial`, `data_exception`, or `blocked`; only `verified`
  reports in `live` mode can send notifier recommendations. The default is
  `shadow`, which computes candidates but withholds actions.
- Rejects narration that changes deterministic evidence, introduces unsupported
  conclusions, or displays numbers absent from the structured payload.
- Emits a terminal audit record with rule version, coverage, gate outcome, and
  approved actions. An emergency kill switch suppresses all recommendations.
- Filters prohibited directive language and visibly verifies the final report.

## Files

- `build_t40.py` — canonical, self-contained source.
- `T40---AlphaWalk-Morning-Command-Center-v1.3.0.json` — generated import file.
- `test_t40.py` — offline structure, engine, degradation, and verifier goldens.
- `backtest_t40.py` — point-in-time fixed-rule evaluator for dated close data.
- `validate_t40_live_capture.py` — release gate for a captured staging run.

## Build and test

```bash
python3 alphawalk/build_t40.py
python3 alphawalk/test_t40.py
```

Evaluate a point-in-time historical universe:

```bash
python3 alphawalk/backtest_t40.py prices.csv \
  --watchlist AAPL,MSFT,NVDA --cost-bps 10 --events-out events.json
```

Validate a staging capture:

```bash
python3 alphawalk/validate_t40_live_capture.py staging-capture.json
```

Keep `recommendation_mode=shadow` until both the historical acceptance criteria
and live-capture gate pass. Promotion changes only that parameter to `live`.
Rollback is immediate: set `emergency_kill_switch=true` or mode to `off`, then
restore the last verified template export if the workflow itself is defective.
The web and market-data agents cannot be fully exercised by the offline harness.
