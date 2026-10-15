"""Read-only adapter from independently audited frozen ETF season standings to Arena.

No ranking before the complete registered season. No live trading assertions.
"""
from research.edge_paper_league import standings

def frozen_league_arena(ledger, *, as_of):
    result = standings(ledger, as_of=as_of)
    if result["schema"] != "oracle-q-paper-league-v1" or result["orders_enabled"] is not False:
        raise ValueError("invalid frozen league evidence")
    rows = []
    for team in result["teams"]:
        status = team["status"]
        if status not in ("INCOMPLETE_EVIDENCE", "ACCUMULATING_FORWARD_EVIDENCE", "FIXED_WINDOW_DESCRIPTIVE_RESULT"):
            raise ValueError("unexpected league team status")
        complete = status == "FIXED_WINDOW_DESCRIPTIVE_RESULT"
        if complete and team["completed_common_sessions"] != team["required_sessions"]:
            raise ValueError("unearned completed season")
        rows.append({
            "candidate_id": team["team"] + "::frozen-three-strategy-basket",
            "market": team["team"], "status": status,
            "completed_common_sessions": team["completed_common_sessions"],
            "required_sessions": team["required_sessions"],
            "missing_eligible_windows": team["missing_eligible_windows"],
            "net_return_pct": team["net_return_pct"] if complete else None,
            "max_drawdown_pct": team["max_drawdown_pct"] if complete else None,
            "edge_proven": False, "eligible_for_live_trading": False
        })
    return {"schema": "oracle-q-arena-frozen-league-v1",
            "source_kind": "AUDITED_FROZEN_PAPER_LEAGUE",
            "season_id": result["season_id"],
            "as_of": result["as_of"],
            "ledger_head_sha256": result["ledger_head_sha256"],
            "rules_sha256": result["rules_sha256"],
            "live": False, "orders_enabled": False, "edge_proven": False,
            "rows": rows,
            "warning": "Fixed prospective paper strategies, not autonomous agents or real-money profits. Descriptive rankings require 60 common sessions. Source/provider authenticity is not independently established."}
