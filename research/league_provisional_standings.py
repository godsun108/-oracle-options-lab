"""Provisional research standings, not registered competition results.

Only fully comparable 18-agent audited open-to-open observations are included.
No intraday day-trade award, official points or championship certification.
"""
from research.league_fixtures import MARKETS, STRATEGIES
from research.league_session_adapter import session_returns
from research.league_scoring import daily_duel, daily_crown, weekly_market_returns


def project(portfolios, sessions):
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError("sorted unique requested sessions required")
    rows = session_returns(portfolios)
    agents = [m + "::" + s for m in MARKETS for s in STRATEGIES]
    included = [day for day in sessions if all((day, agent) in rows for agent in agents)]
    excluded = [day for day in sessions if day not in included]
    days = []
    for day in included:
        evidence = {agent: rows[day, agent] for agent in agents}
        matches = []
        crowns = []
        for market in MARKETS:
            names = [market + "::" + s for s in STRATEGIES]
            # Rotate three pairings; the third agent gets a bye.
            idx = sessions.index(day) % 3
            left, right = ((0, 1), (0, 2), (1, 2))[idx]
            matches.append(daily_duel(day, names[left], names[right], evidence))
            crowns.append(daily_crown(day, market, evidence))
        days.append({"session": day, "duels": matches, "market_crowns": crowns})
    weekly = weekly_market_returns(included, rows) if included else None
    return {
        "schema": "oracle-q-provisional-paper-league-v1",
        "status": "RESEARCH_ONLY_NOT_REGISTERED",
        "requested_sessions": sessions,
        "included_complete_sessions": included,
        "complete_session_count": len(included),
        "agent_count": len(agents),
        "daily_matches_eligible_for_provisional_scoring": len(included) * len(MARKETS),
        "evidence_readiness": "COMPLETE_COMPARABLE_OPEN_TO_OPEN_MARKS" if included else "INSUFFICIENT_COMPARABLE_MARKS",
        "excluded_incomplete_sessions": excluded,
        "daily": days,
        "comparable_market_returns": weekly,
        "official_points_awarded": False,
        "day_trade_winners_declared": False,
        "season_champion_declared": False,
        "orders_enabled": False,
        "edge_proven": False,
        "warning": "Provisional open-to-open paper comparisons; not intraday trading or official registered-season standings.",
    }
