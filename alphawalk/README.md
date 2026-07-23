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
  watchlist lanes are healthy and directionally aligned. Leads are capped at
  three, never use Strong, and can be disabled with a workflow toggle.
- Filters prohibited directive language and visibly verifies the final report.

## Files

- `build_t40.py` — canonical, self-contained source.
- `T40---AlphaWalk-Morning-Command-Center-v1.1.0.json` — generated import file.
- `test_t40.py` — offline structure, engine, degradation, and verifier goldens.

## Build and test

```bash
python3 alphawalk/build_t40.py
python3 alphawalk/test_t40.py
```

Before publishing, import the generated JSON into a staging workspace and run
one live smoke test. Confirm all source-status lines, the notifier payload, and
the visible verification banner. The web and market-data agents cannot be
fully exercised by the offline harness.
