"""Deterministic prospective fixtures for a future Oracle-Q competition.

This module schedules matchups, not winners. Scores require reviewed,
same-session net returns; no daily prices or intraday fills are invented.
"""
from itertools import combinations

MARKETS = ("SPY", "QQQ", "IWM", "SMH", "TLT", "GLD")
STRATEGIES = ("tsmom_63", "trend_200", "reversal_5")


def round_robin(competitors):
    """Each unordered pair meets once, with a deterministic fixture order."""
    names = tuple(competitors)
    if len(names) != len(set(names)) or len(names) < 2:
        raise ValueError("unique competitors required")
    return [list(pair) for pair in combinations(names, 2)]


def league_plan():
    within = {market: round_robin([market + "::" + s for s in STRATEGIES])
              for market in MARKETS}
    return {
        "schema": "oracle-q-prospective-league-fixtures-v1",
        "status": "DESIGN_ONLY_NOT_REGISTERED",
        "daily_within_market_rotation": within,
        "weekly_cross_market_rotation": round_robin(MARKETS),
        "daily_match_points": {"win": 1, "draw": 0, "loss": 0},
        "daily_crown": "One bonus point for highest strictly positive comparable net session return; ties share no bonus pending reviewed tie policy.",
        "weekly_market_cup": "Each market's three equal-capital strategy returns form an equal-weight net weekly composite; rank only with complete common-session evidence.",
        "season_playoffs": "Qualifiers and tie-breakers must be registered before a new season; no retroactive bracket selection.",
        "profit_metric": "Net hypothetical percentage return on equal starting capital; retain USD P&L separately.",
        "missing_data": "No points awarded where comparable verified observations are missing; no fabricated draws.",
        "orders_enabled": False,
        "winners_declared": False,
    }
