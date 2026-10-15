"""Evidence-only readiness report from the actual replayed portfolio artifact.

No retroactive registered season, official points, intraday trades or live orders.
"""
import argparse
import json
from pathlib import Path

from research.agent_paper_portfolio import verify
from research.agent_equity_history import equity_history
from research.league_fixtures import MARKETS, STRATEGIES
from research.league_provisional_standings import project


def report(source):
    expected = {m + "::" + s for m in MARKETS for s in STRATEGIES}
    if source.get("schema") != "oracle-q-agent-paper-positions-v1":
        raise ValueError("unexpected replay artifact")
    if source.get("source_kind") != "REPLAYED_AUDITED_FORWARD_LEDGER":
        raise ValueError("unreviewed replay source")
    if any(source.get(k) is not False for k in
           ("orders_enabled", "broker_fills_verified", "price_is_live", "edge_proven")):
        raise ValueError("unsafe flags")
    portfolios = source.get("portfolios")
    if not isinstance(portfolios, dict) or set(portfolios) != expected:
        raise ValueError("missing replayed agents")
    dates = set()
    for agent, portfolio in portfolios.items():
        verify(portfolio)
        if portfolio.get("agent_id") != agent or portfolio.get("symbol") != agent.split("::")[0]:
            raise ValueError("agent identity mismatch")
        dates.update(p["observed_at"][:10] for p in equity_history(portfolio)["points"])
    # A return at session D requires both D and the immediately previous
    # exchange session, which project() independently validates for all agents.
    sessions = sorted(dates)
    if not sessions:
        return {"schema": "oracle-q-league-readiness-v1",
                "status": "NO_OBSERVED_OPEN_CHECKPOINTS",
                "observed_checkpoint_dates": [],
                "complete_session_count": 0,
                "included_complete_sessions": [],
                "excluded_incomplete_sessions": [],
                "daily_matches_eligible_for_provisional_scoring": 0,
                "official_points_awarded": False, "orders_enabled": False,
                "edge_proven": False}
    result = project(portfolios, sessions)
    return {"schema": "oracle-q-league-readiness-v1",
            "status": result["evidence_readiness"],
            "source_generated_at": source.get("generated_at"),
            "ledger_head_sha256": source.get("ledger_head_sha256"),
            "observed_checkpoint_dates": sessions,
            "complete_session_count": result["complete_session_count"],
            "included_complete_sessions": result["included_complete_sessions"],
            "excluded_incomplete_sessions": result["excluded_incomplete_sessions"],
            "daily_matches_eligible_for_provisional_scoring":
                result["daily_matches_eligible_for_provisional_scoring"],
            "official_points_awarded": False,
            "day_trade_winners_declared": False,
            "orders_enabled": False, "edge_proven": False,
            "warning": "Open-to-open audited hypothetical observations only; no intraday or official results."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = report(json.loads(Path(args.source).read_text()))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
