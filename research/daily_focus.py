"""Rank observed markets for research attention, not trade entry.

Consumes output from multi_market_observer.py. No broker calls or orders.
"""
import argparse
import json
import math

def rank(payload):
    rows = payload.get("results", [])
    ranked = []
    for row in rows:
        if row.get("status") != "OBSERVATION_ONLY":
            continue
        if row.get("bars", 0) < 200:
            continue
        if row.get("as_of") != payload.get("cutoff"):
            continue  # Stale market observations cannot be today's focus.
        ret = row.get("ret5")
        if not isinstance(ret, (int, float)) or not math.isfinite(ret):
            continue
        # Descriptive attention score only, NOT expected return or edge.
        attention = abs(ret)
        ranked.append({"symbol": row["symbol"], "attention_score": round(attention, 8),
                       "direction": "up" if ret > 0 else "down" if ret < 0 else "flat",
                       "above_ma200": row["above_ma200"], "qualified_for_trading": False,
                       "reason": "Five-session movement warrants research; no validated edge."})
    ranked.sort(key=lambda x: (-x["attention_score"], x["symbol"]))
    return {"schema": "oracle-q-daily-focus-v0",
            "cutoff": payload.get("cutoff"), "mode": "RESEARCH_ATTENTION_ONLY",
            "orders_enabled": False, "paper_orders_enabled": False,
            "recommended_action": "NO_TRADE",
            "ranking": ranked[:3],
            "markets_evaluated": len(rows),
            "markets_current": len(ranked),
            "limitations": "Magnitude of recent movement is not a predictive signal. No strategy expectancy or transaction-cost model is evaluated."}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="multi_market_observation.json")
    parser.add_argument("--output", default="daily_market_focus.json")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as handle:
        payload = json.load(handle)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(rank(payload), handle, indent=2)
        handle.write("\n")

if __name__ == "__main__":
    main()
