#!/usr/bin/env python3
"""Validate a staging-run capture before T40 may leave shadow mode.

Capture JSON contract:
  command_read, verification_status, compliance_status, publication_state,
  approved_recommendations, notifier_recommendations, delivery_status.
"""
import argparse
import json
import sys


def validate_capture(capture):
    issues = []
    read = capture.get("command_read")
    if not isinstance(read, dict):
        issues.append("command_read missing")
        read = {}
    if read.get("prepublication_state") != "verified":
        issues.append("creation contract is not verified")
    if read.get("expected_latest_session") is None:
        issues.append("expected latest session missing")
    for row in read.get("watchlist") or []:
        symbol = str(row.get("symbol") or "?")
        if row.get("price_validity") != "verified":
            issues.append(symbol + ": price/session not verified")
        if row.get("entity_validity") != "verified":
            issues.append(symbol + ": cross-source identity not verified")
    coverage = read.get("coverage") or {}
    if (coverage.get("coverage_ratio") or 0) < (coverage.get("minimum_coverage") or 1):
        issues.append("watchlist coverage below threshold")
    if capture.get("verification_status") != "pass":
        issues.append("post-render verification did not pass")
    if capture.get("compliance_status") != "ok":
        issues.append("compliance status is not ok")
    if capture.get("publication_state") != "verified":
        issues.append("final publication state is not verified")
    approved = capture.get("approved_recommendations") or []
    notified = capture.get("notifier_recommendations") or []
    if approved != notified:
        issues.append("notifier recommendation payload differs from approved payload")
    if capture.get("delivery_status") != "delivered":
        issues.append("notifier delivery was not confirmed")
    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture_json")
    args = parser.parse_args()
    with open(args.capture_json, encoding="utf-8") as handle:
        capture = json.load(handle)
    issues = validate_capture(capture)
    approved = capture.get("approved_recommendations") or []
    result = {
        "capture": args.capture_json,
        "release_gate": "pass" if not issues else "fail",
        "issues": issues,
        "approved_recommendation_count": len(approved),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
