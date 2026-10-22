"""Compare two reviewed Arena position artifacts without implying realized daily trading gains."""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path

IDS = {m + "::" + s for m in ("SPY", "QQQ", "IWM", "SMH", "TLT", "GLD")
       for s in ("reversal_5", "trend_200", "tsmom_63")}

def compare(previous, current):
    for obj in (previous, current):
        if obj.get("schema") != "oracle-q-arena-agent-positions-v1" or obj.get("source_kind") != "REPLAYED_AUDITED_FORWARD_LEDGER":
            raise ValueError("unreviewed paper evidence")
        if any(obj.get(k) is not False for k in ("orders_enabled", "broker_fills_verified", "price_is_live", "edge_proven")):
            raise ValueError("unsafe flags")
        if not isinstance(obj.get("ledger_head_sha256"), str) or len(obj["ledger_head_sha256"]) != 64:
            raise ValueError("missing ledger lineage")
    before = {x["agent_id"]: x for x in previous["positions"]}
    after = {x["agent_id"]: x for x in current["positions"]}
    if len(previous["positions"]) != 18 or len(current["positions"]) != 18 or set(before) != IDS or set(after) != IDS:
        raise ValueError("missing or duplicate agents")
    prior = datetime.fromisoformat(previous["source_generated_at"].replace("Z", "+00:00"))
    latest = datetime.fromisoformat(current["source_generated_at"].replace("Z", "+00:00"))
    if prior.tzinfo is None or latest.tzinfo is None or latest <= prior:
        raise ValueError("nonsequential evidence")
    if previous["ledger_head_sha256"] == current["ledger_head_sha256"]:
        raise ValueError("unchanged evidence lineage")
    rows = []
    for agent in sorted(IDS):
        a, b = before[agent], after[agent]
        for row in (a, b):
            if row.get("symbol") != agent.split("::")[0]:
                raise ValueError("symbol mismatch")
            if any(type(row.get(k)) not in (int, float) or not math.isfinite(row[k]) for k in ("equity", "realized_pnl", "unrealized_pnl")):
                raise ValueError("invalid values")
            if abs(row["equity"] - row["cash"] - row["market_value"]) > 0.0001:
                raise ValueError("unbalanced paper account")
        rows.append({"agent_id": agent, "equity_change": round(b["equity"] - a["equity"], 6),
                     "realized_change": round(b["realized_pnl"] - a["realized_pnl"], 6)})
    total_before = sum(x["equity"] for x in before.values())
    total_after = sum(x["equity"] for x in after.values())
    return {"schema": "oracle-q-arena-paper-delta-v1", "status": "REVIEWED_SNAPSHOT_COMPARISON",
            "source_kind": "REPLAYED_AUDITED_FORWARD_LEDGER", "previous_source_at": previous["source_generated_at"],
            "current_source_at": current["source_generated_at"], "previous_ledger_sha256": previous["ledger_head_sha256"],
            "current_ledger_sha256": current["ledger_head_sha256"], "agent_count": 18,
            "previous_equity": round(total_before, 6), "current_equity": round(total_after, 6),
            "equity_change": round(total_after - total_before, 6),
            "realized_change": round(sum(r["realized_change"] for r in rows), 6),
            "rows": rows, "orders_enabled": False, "broker_fills_verified": False,
            "price_is_live": False, "edge_proven": False,
            "warning": "Change between reviewed hypothetical snapshots, not necessarily one trading day; no broker-confirmed fills or proven edge."}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--previous", required=True)
    p.add_argument("--current", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    try:
        result = compare(json.loads(Path(args.previous).read_text()), json.loads(Path(args.current).read_text()))
    except (ValueError, KeyError, TypeError) as exc:
        result = {"schema": "oracle-q-arena-paper-delta-v1", "status": "NO_COMPARABLE_EVIDENCE",
                  "reason": str(exc), "orders_enabled": False, "broker_fills_verified": False,
                  "edge_proven": False}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

if __name__ == "__main__":
    main()
