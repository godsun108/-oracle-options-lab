"""Read-only admissibility report for archived prospective Oracle-Q observations.

Observations are not trades. No P&L is inferred from quotes.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path


def evaluate(records, overrides=None):
    overrides = overrides or {}
    result = []
    seen = set()
    for name, record in sorted(records.items()):
        if name in seen:
            raise ValueError("duplicate record")
        seen.add(name)
        reasons = []
        try:
            day = date.fromisoformat(name.removesuffix(".json"))
        except ValueError:
            reasons.append("invalid_filename_date")
            day = None
        if record.get("schema_version") != "oracle-q-forward-evidence-v1":
            reasons.append("wrong_schema")
        if record.get("research_only") is not True or record.get("orders_enabled") is not False:
            reasons.append("unsafe_mode")
        source = record.get("underlying_source") or {}
        signal = record.get("canonical_signal") or {}
        if day and (source.get("data_cutoff") != day.isoformat() or
                    signal.get("signal_date") != day.isoformat()):
            reasons.append("date_mismatch")
        if source.get("session_policy") != "exclude_current_date_before_16:15_ET":
            reasons.append("session_policy_unverified")
        for field in ("raw_sha256",):
            digest = source.get(field)
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
                reasons.append("invalid_source_hash")
        if signal.get("signal") is True:
            options = record.get("prospective_options") or {}
            if options.get("status") != "OBSERVED":
                reasons.append("options_not_observed")
            if options.get("signal_date") != (day.isoformat() if day else None):
                reasons.append("options_date_mismatch")
            contract = options.get("selected_contract") or {}
            if contract.get("underlying") != "SPY" or contract.get("provider") != "tradier":
                reasons.append("contract_source_mismatch")
            bid, ask = contract.get("bid"), contract.get("ask")
            if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (bid, ask)) or bid < 0 or ask < bid:
                reasons.append("invalid_quote")
            if not isinstance(options.get("chain_rows"), int) or options["chain_rows"] <= 0:
                reasons.append("invalid_chain_rows")
        override = overrides.get(name, {})
        if override.get("admissible") is False:
            reasons.append("manual_exclusion:" + str(override.get("reason", "unspecified")))
        result.append({"record": name, "observation_admissible": not reasons,
                       "reasons": reasons, "trade_verified": False,
                       "broker_fills_verified": False, "realized_pnl_available": False})
    return {"schema": "oracle-q-forward-observation-admissibility-v1",
            "mode": "RESEARCH_ONLY", "orders_enabled": False,
            "records": result,
            "eligible_observations": sum(x["observation_admissible"] for x in result),
            "trade_verification_status": "NO_BROKER_FILLS_OR_SETTLED_PNL"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("usage: python research/forward_observation_admissibility_v1.py prospective_records/")
    root = Path(sys.argv[1])
    records = {p.name: json.loads(p.read_text()) for p in root.glob("????-??-??.json")}
    overrides_path = root / "admissibility.json"
    overrides = json.loads(overrides_path.read_text()).get("records", {}) if overrides_path.exists() else {}
    print(json.dumps(evaluate(records, overrides), indent=2))
