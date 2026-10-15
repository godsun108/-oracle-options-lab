"""Evidence-gated championship specifications for a future prospective season.

The existing registered 60-session open-to-open league remains unchanged.
"""
SCHEMA = "oracle-q-championship-definitions-v1"

def championship_status(*, intraday_evidence=None, season_complete=False):
    """No winners without reviewed intraday and complete season adjudication."""
    if intraday_evidence:
        raise ValueError("intraday adjudication requires a separately reviewed evidence validator")
    return {
        "schema": SCHEMA,
        "first_profitable_day_trade": {
            "status": "AWAITING_VERIFIED_INTRADAY_EVIDENCE",
            "winner": None,
            "metric": "first positive realized intraday session P&L after hypothetical costs",
            "requirements": [
                "same exchange session entry and exit",
                "timestamped and source-linked entry and exit prices",
                "complete hypothetical costs and strictly positive realized net P&L",
                "separate per-market and cross-market rankings",
                "no overnight positions, unrealized marks or daily-only inference",
            ],
        },
        "most_profitable_season": {
            "status": "AWAITING_REVIEWED_SEASON_ADJUDICATION" if season_complete else "SEASON_IN_PROGRESS",
            "winner": None,
            "metric": "highest net return on equal initial capital across complete identical season windows",
            "requirements": [
                "pre-registered season boundaries and competitors",
                "complete auditable observations for a common window",
                "cost-adjusted net return and separately disclosed drawdown",
                "separate per-market and cross-market rankings",
                "no winners before the season ends",
            ],
        },
        "orders_enabled": False,
        "broker_fills_verified": False,
        "edge_proven": False,
    }
