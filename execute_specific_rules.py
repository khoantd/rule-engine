#!/usr/bin/env python3
"""
Fetch one or more rule definitions from the Rule Engine management API (DB-backed),
then execute exactly that subset by passing them inline to the execution API.

Typical usage:

  python execute_specific_rules.py \
    --base-url http://localhost:8000 \
    --rule-id R0001 --rule-id R0002 \
    --data '{"issue": 35, "publisher": "DC"}' \
    --dry-run
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Iterable, List, Optional

import requests


def _headers(api_key: Optional[str]) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _normalize_rule_for_inline_execution(rule: Dict[str, Any]) -> Dict[str, Any]:
    """
    The engine accepts rules shaped like the configured rules payload and is tolerant
    of a few legacy aliases. This normalizes the most common ones so callers can
    pass through DB-returned shapes safely.
    """
    normalized = dict(rule)

    # Ensure rule name uses the expected key.
    if "rule_name" not in normalized and "rulename" in normalized:
        normalized["rule_name"] = normalized.get("rulename")

    # Normalize points key.
    if "rule_point" not in normalized and "rulepoint" in normalized:
        normalized["rule_point"] = normalized.get("rulepoint")

    # Keep only JSON-serializable primitives/objects (defensive; DB models sometimes add extras).
    # If the server supports more keys, it will ignore unknowns safely; we don't over-prune here.
    return normalized


def fetch_rule(base_url: str, rule_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/v1/management/rules/{rule_id}"
    resp = requests.get(url, headers=_headers(api_key), timeout=30)
    resp.raise_for_status()
    body: Dict[str, Any] = resp.json()
    return body


def execute_inline_rules(
    base_url: str,
    rules: List[Dict[str, Any]],
    data: Dict[str, Any],
    *,
    dry_run: bool = True,
    consumer_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/v1/rules/execute"
    payload: Dict[str, Any] = {
        "data": data,
        "dry_run": dry_run,
        "consumer_id": consumer_id,
        "correlation_id": correlation_id,
        "rules": rules,
    }
    resp = requests.post(url, headers=_headers(api_key), json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _parse_json_arg(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON: {e}") from e


def _ensure_dict(value: Any, *, name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"--{name} must be a JSON object (got {type(value).__name__})")
    return value


def _dedupe_preserve_order(values: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute specific rule(s) via existing APIs")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--rule-id", action="append", required=True, help="Repeatable rule id")
    parser.add_argument("--data", required=True, help="Input facts as JSON object string")
    parser.add_argument("--dry-run", action="store_true", help="Return per-rule evaluations")
    parser.add_argument("--consumer-id", default=None)
    parser.add_argument("--correlation-id", default=None)
    args = parser.parse_args()

    data = _ensure_dict(_parse_json_arg(args.data), name="data")
    rule_ids = _dedupe_preserve_order(args.rule_id)

    fetched_rules: List[Dict[str, Any]] = []
    for rid in rule_ids:
        fetched = fetch_rule(args.base_url, rid, api_key=args.api_key)
        fetched_rules.append(_normalize_rule_for_inline_execution(fetched))

    result = execute_inline_rules(
        args.base_url,
        fetched_rules,
        data,
        dry_run=bool(args.dry_run),
        consumer_id=args.consumer_id,
        correlation_id=args.correlation_id,
        api_key=args.api_key,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

