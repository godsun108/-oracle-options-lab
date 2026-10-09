"""Read-only Tradier SPX and FRED SP500 production comparison.

Fetches only the bounded recent FRED overlap. Any source failure writes
an explicit unverified status and never promotes historical ATH coverage.
"""
import argparse
import json
import os
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from research.multi_market_observer import request_history
from research.paco_spx_fred_crosscheck import compare


def produce(fred_evidence, token, *, fetch=request_history, today=None):
    base = {
        "schema": "paco-spx-fred-live-crosscheck-v1",
        "status": "SOURCE_UNAVAILABLE",
        "orders_enabled": False,
        "history_coverage_complete_verified": False,
        "strategy_profitability_proven": False,
        "fred_sha256": fred_evidence.get("sha256"),
        "source": "Tradier SPX and FRED SP500",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat()
    }
    observations = fred_evidence.get("observations")
    if not token or not isinstance(observations, list) or not observations:
        return base
    now = today or date.today()
    start = now - timedelta(days=45)
    try:
        tradier = fetch("SPX", token, start.isoformat(), now.isoformat())
        if not isinstance(tradier, list):
            return base
        result = compare(tradier, observations)
        base.update(result)
        base["schema"] = "paco-spx-fred-live-crosscheck-v1"
        base["fred_sha256"] = fred_evidence.get("sha256")
        base["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
        return base
    except (ValueError, TypeError, KeyError, TimeoutError, OSError) as exc:
        base["error_type"] = type(exc).__name__
        return base


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fred", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    fred = json.loads(Path(args.fred).read_text())
    result = produce(fred, os.getenv("TRADIER_TOKEN"))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PACO FRED-Tradier production crosscheck:", result["status"],
          "compared:", result.get("compared_dates", 0),
          "mismatches:", result.get("mismatch_count", 0))


if __name__ == "__main__":
    main()
