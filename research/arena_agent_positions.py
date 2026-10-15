"""Strict public projection of reviewed simulated agent positions.

Rejects inconsistent accounting and does not publish internal event histories.
"""
import argparse
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from research.agent_paper_portfolio import verify as verify_portfolio, snapshot as portfolio_snapshot
from research.edge_lab import IDS
from research.multi_market_observer import SYMBOLS

def project(source, *, now=None):
    if source.get("schema") != "oracle-q-agent-paper-positions-v1" or source.get("source_kind") != "REPLAYED_AUDITED_FORWARD_LEDGER":
        raise ValueError("unexpected source")
    for key in ("orders_enabled", "broker_fills_verified", "price_is_live", "edge_proven"):
        if source.get(key) is not False:
            raise ValueError("unsafe publication flag")
    expected = {m + "::" + s for m in SYMBOLS for s in IDS}
    rows = source.get("positions")
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError("missing agents")
    portfolios = source.get('portfolios')
    if not isinstance(portfolios, dict) or set(portfolios) != expected:
        raise ValueError('missing original agent portfolios')
    seen = set()
    output = []
    for row in rows:
        agent = row.get("agent_id")
        if agent not in expected or agent in seen or row.get("symbol") != agent.split("::")[0]:
            raise ValueError("unexpected or duplicate agent")
        seen.add(agent)
        original = portfolios[agent]
        verify_portfolio(original)
        if original.get('agent_id') != agent or original.get('symbol') != row['symbol']:
            raise ValueError('portfolio identity mismatch')
        if portfolio_snapshot(original) != row:
            raise ValueError('published position does not match audited portfolio events')
        if any(row.get(k) is not False for k in ("orders_enabled", "broker_fills_verified", "price_is_live", "edge_proven")):
            raise ValueError("agent cannot claim live fills or proven edge")
        side = row.get("side")
        if side not in ("LONG", "FLAT"):
            raise ValueError("unsupported position")
        numeric = ("quantity", "cash", "market_value", "equity", "realized_pnl", "unrealized_pnl")
        if any(type(row.get(k)) not in (int, float) or not math.isfinite(row[k]) for k in numeric):
            raise ValueError("invalid accounting")
        qty = row["quantity"]
        if qty < 0 or row["cash"] < -0.000001 or abs(row["equity"] - row["cash"] - row["market_value"]) > 0.00001:
            raise ValueError("unbalanced account")
        entry = row.get("average_entry")
        if (side == "FLAT") != (qty == 0) or (side == "FLAT") != (entry is None):
            raise ValueError("inconsistent position")
        if side == "LONG" and (type(entry) not in (int, float) or not math.isfinite(entry) or entry <= 0):
            raise ValueError("invalid entry")
        mark = row.get("last_mark")
        if mark is not None:
            if type(mark.get("price")) not in (int, float) or not math.isfinite(mark["price"]) or mark["price"] <= 0:
                raise ValueError("invalid mark")
            observed = datetime.fromisoformat(mark["observed_at"].replace("Z", "+00:00"))
            if observed.tzinfo is None:
                raise ValueError("mark without timezone")
            if observed > (now or datetime.now(timezone.utc)) + timedelta(minutes=5):
                raise ValueError("future mark")
            if abs(row["market_value"] - qty * mark["price"]) > 0.00001:
                raise ValueError("market value mismatch")
        elif qty:
            raise ValueError("holding without mark")
        output.append({k: row[k] for k in ("agent_id", "symbol", "side", "quantity", "average_entry",
                      "cash", "market_value", "equity", "realized_pnl", "unrealized_pnl", "last_mark")})
    return {"schema": "oracle-q-arena-agent-positions-v1",
            "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
            "source_generated_at": source["generated_at"],
            "source_kind": "REPLAYED_AUDITED_FORWARD_LEDGER",
            "ledger_head_sha256": source["ledger_head_sha256"],
            "orders_enabled": False, "broker_fills_verified": False, "price_is_live": False,
            "edge_proven": False, "positions": output,
            "warning": "Daily historical opening-price replay, not live prices or broker-confirmed paper fills."}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = project(json.loads(Path(args.source).read_text()))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

if __name__ == "__main__":
    main()
