"""Export explicitly non-live Arena snapshots from shadow league scorecards."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from research.challenger_registry import canonical_digest

def arena_feed(scorecard, *, generated_at):
    if not isinstance(scorecard, dict) or scorecard.get("schema") != "oracle-q-shadow-league-score-v1":
        raise ValueError("unrecognized scorecard")
    if scorecard.get("orders_enabled") is not False or scorecard.get("promotion_authorized") is not False:
        raise ValueError("unsafe scorecard flags")
    rows = scorecard.get("rows")
    if not isinstance(rows, list):
        raise ValueError("missing rows")
    # Preserve all rows, including incomplete evidence, for transparent display.
    allowed = {"candidate_id","market","status","missing_windows","net_profit_usd",
               "net_return_pct","first_positive_window","max_drawdown_pct",
               "edge_proven","eligible_for_live_trading"}
    for row in rows:
        if not isinstance(row, dict) or not allowed.issubset(row):
            raise ValueError("invalid competitor row")
        if row["edge_proven"] is not False or row["eligible_for_live_trading"] is not False:
            raise ValueError("unsupported evidence claim")
    timestamp = datetime.fromisoformat(generated_at.replace("Z","+00:00"))
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp requires timezone")
    return {"schema":"oracle-q-arena-feed-v1",
            "generated_at":timestamp.isoformat(),
            "source_scorecard_sha256":canonical_digest(scorecard),
            "source_kind":"RESEARCH_PAPER_SNAPSHOT",
            "live":False,"orders_enabled":False,"edge_proven":False,
            "rows":[{k:r[k] for k in sorted(allowed)} for r in rows],
            "warning":"Snapshot only. No realtime feed, broker fills, or independently proven profitability."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--scorecard",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    source=json.loads(Path(args.scorecard).read_text())
    result=arena_feed(source,generated_at=datetime.now(timezone.utc).isoformat())
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Arena snapshot:",len(result["rows"]),"rows; live:",result["live"])

if __name__=="__main__":
    main()
