"""Offline comparison of FRED SP500 observations and Tradier SPX closes.

Both inputs must be supplied independently. This module never fetches, trades,
or certifies full historical coverage.
"""
import argparse
import json
import math
from datetime import date
from pathlib import Path


def _values(rows, *, date_key, close_key):
    result = {}
    for row in rows:
        try:
            day = date.fromisoformat(str(row[date_key])[:10]).isoformat()
            price = float(row[close_key])
            if math.isfinite(price) and price > 0:
                result[day] = price
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
    return result


def compare(tradier, fred, *, tolerance=0.02):
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be nonnegative and finite")
    t = _values(tradier, date_key="date", close_key="close")
    f = _values(fred, date_key="date", close_key="value")
    dates = sorted(set(t) & set(f))
    mismatches = [{"date": day, "tradier_close": t[day], "fred_close": f[day],
                   "absolute_difference": round(abs(t[day]-f[day]), 6)}
                  for day in dates if abs(t[day]-f[day]) > tolerance]
    return {
        "schema": "paco-spx-fred-crosscheck-v1",
        "source_a": "Tradier SPX daily close",
        "source_b": "FRED SP500 daily close (S&P Dow Jones Indices)",
        "fred_source_url": "https://fred.stlouisfed.org/series/SP500",
        "status": "NO_OVERLAP" if not dates else ("MISMATCHES_FOUND" if mismatches else "OVERLAP_MATCHED"),
        "compared_dates": len(dates),
        "tradier_valid_dates": len(t),
        "fred_valid_dates": len(f),
        "fred_dates_missing_from_tradier": len(set(f)-set(t)),
        "tradier_dates_missing_from_fred": len(set(t)-set(f)),
        "first_compared_date": dates[0] if dates else None,
        "last_compared_date": dates[-1] if dates else None,
        "tolerance_index_points": tolerance,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:100],
        "mismatch_list_truncated": len(mismatches) > 100,
        "history_coverage_complete_verified": False,
        "strategy_profitability_proven": False,
        "orders_enabled": False,
        "warning": "Overlap matching does not establish complete historical coverage or a true all-time high."
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tradier", required=True, help="JSON list of {date,close} daily bars")
    p.add_argument("--fred", required=True, help="FRED JSON observations list or object with observations")
    p.add_argument("--output", required=True)
    p.add_argument("--tolerance", type=float, default=0.02)
    args = p.parse_args()
    tradier = json.loads(Path(args.tradier).read_text())
    fred = json.loads(Path(args.fred).read_text())
    if isinstance(fred, dict):
        fred = fred["observations"]
    result = compare(tradier, fred, tolerance=args.tolerance)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print("PACO SPX FRED cross-check:", result["status"], "overlap:", result["compared_dates"],
          "mismatches:", result["mismatch_count"])


if __name__ == "__main__":
    main()
