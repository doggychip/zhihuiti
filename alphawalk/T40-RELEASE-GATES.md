# T40 Release Gates

T40 v1.3 starts in `shadow` mode. Do not switch to `live` until every gate below
has an attached artifact and named approver.

## 1. Historical evaluation

- Input universe is point-in-time and includes delisted/renamed constituents.
- Prices are corporate-action adjusted and contain no future revisions.
- Costs include the approved spread, slippage, and fee assumption.
- Results are segmented by Buy/Sell, market regime, and 1/5/20-session horizon.
- Acceptance thresholds are written **before** reviewing results:
  - minimum event count: `[OWNER TO SET]`
  - minimum net excess return: `[OWNER TO SET]`
  - maximum adverse result/drawdown: `[OWNER TO SET]`
  - minimum coverage: `80%` (template contract)
- Evaluation command and immutable input checksum are retained.

## 2. Staging capture

- Import succeeds without schema translation.
- All six market proxies carry dated regular-session records.
- Each watchlist row has concordant Yahoo/Finnhub identity.
- Expected completed exchange session is correct.
- Report status is `verified`; verifier and compliance both pass.
- Approved and notifier recommendation payloads are byte-for-byte equivalent.
- Delivery status is `delivered`.
- `validate_t40_live_capture.py` exits zero.

## 3. Failure matrix

Confirm no notifier recommendations for:

- stale, future-dated, or malformed prices;
- weekend/holiday session mistakes;
- missing or conflicting issuer identity;
- wrong exchange, currency, or timezone;
- watchlist coverage below 80%;
- partial/failed source lanes;
- mixed or unavailable market regime;
- invented narrative numbers or unsupported conclusions;
- compliance redaction, verifier review, or notifier failure;
- recommendation mode `shadow`/`off` or active emergency kill switch.

## 4. Governance and rollback

- Product/compliance owner approves Tier-B Buy/Sell mapping and disclaimer.
- Data entitlements and source attribution are documented.
- Audit retention and monitoring owner are assigned.
- `emergency_kill_switch=true` has been exercised in staging.
- Last verified template export and rollback instructions are accessible.

## 5. Promotion

Promotion is a configuration-only change:

```text
recommendations_enabled = true
recommendation_mode = live
emergency_kill_switch = false
```

Any gate regression returns the workflow to `shadow` or activates the kill
switch. Historical performance is evidence about a fixed sample, not a promise
of future results.
