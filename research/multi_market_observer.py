"""Read-only multi-market Tradier observation collector. Never places orders."""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

SYMBOLS = ("SPY", "QQQ", "IWM", "SMH", "TLT", "GLD")
EASTERN = ZoneInfo("America/New_York")
BASE = "https://api.tradier.com/v1"
MIN_BARS = 200


def eligible_cutoff(now=None):
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(EASTERN)
    # Do not include a current-day bar before the normal cash-session close + 15m.
    if now.weekday() < 5 and (now.hour, now.minute) >= (16, 15):
        return now.date()
    return now.date() - dt.timedelta(days=1)


def request_history(symbol, token, start, end):
    params = urllib.parse.urlencode({"symbol": symbol, "interval": "daily", "start": start, "end": end})
    req = urllib.request.Request(BASE + "/markets/history?" + params, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "User-Agent": "oracle-q-multi-market-observer/1",
    })
    with urllib.request.urlopen(req, timeout=25) as response:
        payload = json.load(response)
    history = payload.get("history") or {}
    days = history.get("day") or []
    return [days] if isinstance(days, dict) else days


def summarize(symbol, rows, cutoff):
    clean = {}
    for row in rows:
        try:
            date = dt.date.fromisoformat(str(row["date"])[:10])
            close = float(row["close"])
            if close <= 0 or date > cutoff:
                continue
            clean[date.isoformat()] = close
        except (KeyError, ValueError, TypeError):
            continue
    ordered = sorted(clean.items())
    out = {"symbol": symbol, "cutoff": cutoff.isoformat(), "bars": len(ordered),
           "status": "INSUFFICIENT_DATA", "signal": None}
    if len(ordered) < MIN_BARS:
        return out
    closes = [value for _, value in ordered]
    latest = closes[-1]
    ma200 = sum(closes[-200:]) / 200
    ret5 = latest / closes[-6] - 1 if len(closes) >= 6 else None
    out.update({"status": "OBSERVATION_ONLY", "as_of": ordered[-1][0],
                "close": round(latest, 6), "ma200": round(ma200, 6),
                "ret5": round(ret5, 8) if ret5 is not None else None,
                "above_ma200": latest > ma200,
                "signal": None})  # Do not invent strategy rules.
    return out


def collect(token, now=None, fetch=request_history):
    cutoff = eligible_cutoff(now)
    start = (cutoff - dt.timedelta(days=850)).isoformat()
    results = []
    for symbol in SYMBOLS:
        try:
            rows = fetch(symbol, token, start, cutoff.isoformat())
            results.append(summarize(symbol, rows, cutoff))
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
            results.append({"symbol": symbol, "status": "DATA_ERROR",
                            "error_type": type(exc).__name__, "signal": None})
    payload = {"schema": "oracle-q-multi-market-observation-v1",
               "cutoff": cutoff.isoformat(), "research_only": True,
               "orders_enabled": False, "strategies_enabled": False,
               "provider": "tradier", "results": results}
    payload["sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="multi_market_observation.json")
    args = parser.parse_args()
    token = os.getenv("TRADIER_TOKEN", "")
    if not token:
        print("TRADIER_TOKEN missing; no observation collected", file=sys.stderr)
        return 2
    payload = collect(token)
    with open(args.output, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    failures = [r for r in payload["results"] if r["status"] != "OBSERVATION_ONLY"]
    print("Observed", len(payload["results"]), "markets; unavailable/insufficient:", len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
