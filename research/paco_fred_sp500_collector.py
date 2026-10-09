"""Fetch FRED SP500 CSV for independent research; never enable trades or ATH verification."""
import argparse
import csv
import hashlib
import io
import json
import math
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


def collect(*, opener=urllib.request.urlopen):
    request = urllib.request.Request(URL, headers={"User-Agent": "OracleQ-Research/1.0"})
    with opener(request, timeout=20) as response:
        raw = response.read(MAX_BYTES + 1)
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
    result = collect()
    Path(args.output).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("FRED SP500 fetched:", result["observation_count"], "dates", result["first_date"], result["last_date"])


if __name__ == "__main__":
    main()
