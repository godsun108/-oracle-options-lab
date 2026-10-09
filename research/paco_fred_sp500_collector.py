"""Fetch FRED SP500 CSV for independent research; never enable trades or ATH verification."""
import argparse
import csv
import hashlib
import io
import json
import math
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500"
MAX_BYTES = 3_000_000


def parse_csv(data):
    reader = csv.DictReader(io.StringIO(data))
    if not reader.fieldnames or "SP500" not in reader.fieldnames:
        raise ValueError("Expected SP500 column")
    date_column = "observation_date" if "observation_date" in reader.fieldnames else "DATE"
    if date_column not in reader.fieldnames:
        raise ValueError("Expected date column")
    rows = []
    for row in reader:
        try:
            d = date.fromisoformat(row[date_column])
            value = float(row["SP500"])
            if math.isfinite(value) and value > 0:
                rows.append({"date": d.isoformat(), "value": value})
        except (ValueError, TypeError, KeyError):
            continue
    if not rows:
        raise ValueError("No valid SP500 prices")
    return rows


def collect(*, opener=urllib.request.urlopen, attempts=2, timeout=12, sleeper=time.sleep):
    if not 1 <= attempts <= 3 or not 1 <= timeout <= 30:
        raise ValueError("invalid bounded fetch settings")
    request = urllib.request.Request(URL, headers={"User-Agent": "OracleQ-Research/1.0"})
    last_error = None
    for attempt in range(attempts):
        try:
            with opener(request, timeout=timeout) as response:
                raw = response.read(MAX_BYTES + 1)
            break
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                sleeper(1)
    else:
        raise last_error
    if len(raw) > MAX_BYTES:
        raise ValueError("FRED CSV exceeds maximum size")
    rows = parse_csv(raw.decode("utf-8-sig"))
    return {
        "schema": "paco-fred-sp500-evidence-v1",
        "source": "FRED SP500 (S&P Dow Jones Indices LLC)",
        "source_url": URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "observations": rows,
        "observation_count": len(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "history_coverage_complete_verified": False,
        "orders_enabled": False,
        "warning": "FRED SP500 is a limited rolling history and is not full ATH verification."
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    args = p.parse_args()
    try:
        result = collect()
        result["status"] = "COLLECTED"
    except (TimeoutError, OSError, urllib.error.URLError, ValueError, UnicodeError, csv.Error) as exc:
        result = {
            "schema": "paco-fred-sp500-evidence-v1",
            "status": "SOURCE_UNAVAILABLE",
            "error_type": type(exc).__name__,
            "source_url": URL,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "observations": [],
            "observation_count": 0,
            "history_coverage_complete_verified": False,
            "orders_enabled": False,
        }
    Path(args.output).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("FRED SP500 collection:", result["status"], "observations:", result["observation_count"])
    if result["status"] != "COLLECTED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
