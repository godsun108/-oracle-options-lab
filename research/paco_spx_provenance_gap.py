"""Report historical SPX coverage against the index provider's published first-value date.

This is a provenance gap diagnostic, not independent price verification.
Never promotes the strategy signal or historical coverage flag.
"""
import argparse
import json
from datetime import date
from pathlib import Path

OFFICIAL_FIRST_VALUE = date(1928, 1, 3)
OFFICIAL_LAUNCH = date(1957, 3, 4)
METHODOLOGY = "https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf"


def assess(diagnostic):
    result = {
        "schema": "paco-spx-provenance-gap-v1",
        "source": "S&P Dow Jones Indices S&P U.S. Indices Methodology",
        "methodology_url": METHODOLOGY,
        "official_first_value_date": OFFICIAL_FIRST_VALUE.isoformat(),
        "official_launch_date": OFFICIAL_LAUNCH.isoformat(),
        "history_coverage_complete_verified": False,
        "independent_price_series_verified": False,
        "orders_enabled": False,
        "status": "UNVERIFIED_SOURCE_HISTORY",
        "tradier_first_date": None,
        "tradier_last_date": None,
        "tradier_bars": 0,
        "warning": "Provider dates are metadata, not an independently validated daily price dataset."
    }
    entries = diagnostic.get("symbols", [])
    spx = next((x for x in entries if x.get("symbol") == "SPX" and x.get("status") == "HISTORY_RETURNED"), None)
    if not spx:
        return result
    try:
        first = date.fromisoformat(spx["first_date"])
        last = date.fromisoformat(spx["last_date"])
        bars = int(spx["bars"])
        if bars <= 0 or last < first:
            return result
    except (ValueError, TypeError, KeyError, OverflowError):
        return result
    result.update(tradier_first_date=first.isoformat(), tradier_last_date=last.isoformat(), tradier_bars=bars)
    if first > OFFICIAL_FIRST_VALUE:
        result["status"] = "HISTORICAL_PREFIX_MISSING"
        result["missing_before_tradier_start"] = {
            "from": OFFICIAL_FIRST_VALUE.isoformat(),
            "through_exclusive": first.isoformat()
        }
    else:
        result["status"] = "DATE_COVERAGE_UNVERIFIED"
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--diagnostic", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    report = assess(json.loads(Path(args.diagnostic).read_text()))
    Path(args.output).write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("PACO SPX provenance gap:", report["status"], "coverage verified:", report["history_coverage_complete_verified"])


if __name__ == "__main__":
    main()
