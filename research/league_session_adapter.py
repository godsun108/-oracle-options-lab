"""Conservative adapter: audited hypothetical event marks -> session returns.

Requires consecutive exchange sessions and a mark at each opening boundary.
Does not assert intraday P&L, execution fills or proven daily profitability.
"""
from datetime import datetime
import math

from research.agent_paper_portfolio import verify
from research.agent_equity_history import equity_history
from research.edge_session_calendar import next_session, session_bounds
from research.league_fixtures import MARKETS, STRATEGIES


def session_returns(portfolios):
    expected = {m + "::" + s for m in MARKETS for s in STRATEGIES}
    if not isinstance(portfolios, dict) or set(portfolios) != expected:
        raise ValueError("all eighteen portfolios required")
    result = {}
    for agent in sorted(expected):
        portfolio = portfolios[agent]
        verify(portfolio)
        if portfolio["agent_id"] != agent or portfolio["symbol"] != agent.split("::")[0]:
            raise ValueError("portfolio identity mismatch")
        marks = equity_history(portfolio)["points"]
        previous = None
        for point in marks:
            stamp = datetime.fromisoformat(point["observed_at"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timezone required")
            day = stamp.date().isoformat()
            if stamp != session_bounds(day)[0]:
                raise ValueError("non-opening checkpoint is not a verified session boundary")
            if previous is not None:
                prior_day, prior_equity = previous
                if day <= prior_day:
                    raise ValueError("non-monotonic event marks")
                if next_session(prior_day) == day:
                    if prior_equity <= 0 or not math.isfinite(prior_equity):
                        raise ValueError("invalid prior equity")
                    key = day, agent
                    result[key] = {
                        "session": day, "agent_id": agent,
                        "net_return_pct": 100 * (point["equity"] / prior_equity - 1),
                        "audited": True, "complete": True,
                        "orders_enabled": False, "broker_fills_verified": False,
                        "source": "CONSECUTIVE_AUDITED_OPEN_TO_OPEN_PAPER_MARKS",
                        "not_intraday_day_trade": True,
                        "start_mark_sha256": previous_sha,
                        "end_mark_sha256": point["event_sha256"],
                    }
            previous = day, point["equity"]
            previous_sha = point["event_sha256"]
    return result
