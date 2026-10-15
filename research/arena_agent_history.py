"""Publish only independently verified hypothetical event-mark histories."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from research.agent_equity_history import equity_history
from research.agent_paper_portfolio import snapshot, verify
from research.edge_lab import IDS
from research.multi_market_observer import SYMBOLS


def project(source):
    if source.get("schema") != "oracle-q-agent-paper-positions-v1" or source.get("source_kind") != "REPLAYED_AUDITED_FORWARD_LEDGER":
        raise ValueError("unexpected source")
    if any(source.get(k) is not False for k in ("orders_enabled", "broker_fills_verified", "price_is_live", "edge_proven")):
        raise ValueError("unsafe source")
    expected = {symbol + "::" + strategy for symbol in SYMBOLS for strategy in IDS}
    portfolios = source.get("portfolios")
    positions = source.get("positions")
    if not isinstance(portfolios, dict) or set(portfolios) != expected or not isinstance(positions, list) or len(positions) != len(expected):
        raise ValueError("incomplete agent evidence")
    indexed = {p["agent_id"]: p for p in positions}
    if set(indexed) != expected or len(indexed) != len(positions):
        raise ValueError("missing or duplicate positions")
    histories = []
    for agent in sorted(expected):
        portfolio = portfolios[agent]
        verify(portfolio)
        if portfolio["agent_id"] != agent or portfolio["symbol"] != agent.split("::")[0]:
            raise ValueError("portfolio identity mismatch")
        if snapshot(portfolio) != indexed[agent]:
            raise ValueError("position not derived from portfolio")
        histories.append(equity_history(portfolio))
    return {"schema": "oracle-q-arena-agent-history-v1",
            "source_kind": "AUDITED_HYPOTHETICAL_EVENT_MARKS",
            "source_generated_at": source["generated_at"],
            "ledger_head_sha256": source["ledger_head_sha256"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "orders_enabled": False, "price_is_live": False,
            "broker_fills_verified": False, "edge_proven": False,
            "history_is_daily": False, "promotion_eligible": False,
            "agents": histories,
            "warning": "Event-mark hypothetical equity observations only; not daily or intraday maximum drawdown, real-time prices, broker fills, or proven edge."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = project(json.loads(Path(args.source).read_text()))
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
