"""Canonicalize and fingerprint public Data API trade observations."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from zhihuiti.polymarket.models import Side, SourceTrade


def _required_decimal(payload: dict[str, Any], name: str) -> Decimal:
    try:
        value = Decimal(str(payload[name]))
    except (KeyError, InvalidOperation) as exc:
        raise ValueError(f"invalid or missing {name}") from exc
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{name} must be a positive finite decimal")
    return value


def _identity(payload: dict[str, Any], wallet: str) -> tuple[str, ...]:
    """Fields exposed by the API that identify a fill as closely as possible."""
    return (
        str(payload.get("transactionHash", "")).lower(),
        wallet,
        str(payload.get("asset", "")),
        str(payload.get("conditionId", "")),
        str(payload.get("side", "")).upper(),
        format(_required_decimal(payload, "size").normalize(), "f"),
        format(_required_decimal(payload, "price").normalize(), "f"),
        str(int(payload["timestamp"])),
    )


def normalize_trades(
    payloads: Iterable[dict[str, Any]],
    *,
    expected_wallet: str | None = None,
) -> list[SourceTrade]:
    """Normalize a batch and disambiguate identical same-second observations.

    The public feed has no fill ID or log index. Identical rows are assigned a
    deterministic occurrence number in their API order. The raw row remains
    stored so this unavoidable ambiguity is auditable.
    """
    occurrences: dict[tuple[str, ...], int] = defaultdict(int)
    result: list[SourceTrade] = []
    for raw in payloads:
        wallet = str(raw.get("proxyWallet", expected_wallet or "")).lower()
        if expected_wallet and wallet != expected_wallet.lower():
            continue
        identity = _identity(raw, wallet)
        occurrence = occurrences[identity]
        occurrences[identity] += 1
        canonical = "\x1f".join((*identity, str(occurrence)))
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        try:
            side = Side(str(raw["side"]).upper())
            timestamp = int(raw["timestamp"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("invalid side or timestamp") from exc
        token_id = str(raw.get("asset", ""))
        condition_id = str(raw.get("conditionId", ""))
        if not wallet or not token_id or not condition_id:
            raise ValueError("wallet, asset, and conditionId are required")
        result.append(
            SourceTrade(
                fingerprint=fingerprint,
                wallet=wallet,
                token_id=token_id,
                condition_id=condition_id,
                side=side,
                size=_required_decimal(raw, "size"),
                price=_required_decimal(raw, "price"),
                timestamp=timestamp,
                transaction_hash=str(raw.get("transactionHash", "")).lower(),
                outcome=str(raw.get("outcome", "")),
                title=str(raw.get("title", "")),
                occurrence=occurrence,
                raw=json.loads(json.dumps(raw, default=str)),
            )
        )
    return sorted(result, key=lambda trade: (trade.timestamp, trade.fingerprint))
