"""Event-observed equity history for audited hypothetical portfolios.

Only hash-linked simulated event marks are used. This is not a daily price
series, broker fill history, or evidence of a repeatable trading edge.
"""
import math

from research.agent_paper_portfolio import initialize, transition, snapshot, verify


def equity_history(portfolio):
    verify(portfolio)
    state = initialize(portfolio["agent_id"], portfolio["symbol"],
                       cash=portfolio["starting_cash"])
    points = []
    peak = portfolio["starting_cash"]
    worst_drawdown = 0.0
    for event in portfolio["events"]:
        state = transition(state, target=event["target"],
                           execution_price=event["price"],
                           observed_at=event["observed_at"],
                           cost_bps=event["cost_bps"])
        current = snapshot(state)
        equity = current["equity"]
        if not math.isfinite(equity) or equity < 0:
            raise ValueError("invalid observed equity")
        peak = max(peak, equity)
        drawdown = (equity / peak - 1.0) * 100.0
        worst_drawdown = min(worst_drawdown, drawdown)
        points.append({"observed_at": event["observed_at"],
                       "event_sha256": event["event_sha256"],
                       "equity": equity,
                       "realized_pnl": current["realized_pnl"],
                       "unrealized_pnl": current["unrealized_pnl"],
                       "drawdown_pct": drawdown})
    if state != portfolio:
        raise ValueError("replayed events do not reconstruct portfolio")
    return {"agent_id": portfolio["agent_id"],
            "source": "AUDITED_HYPOTHETICAL_EVENT_MARKS",
            "starting_cash": portfolio["starting_cash"],
            "observed_event_count": len(points),
            "max_observed_drawdown_pct": worst_drawdown,
            "points": points,
            "edge_proven": False, "broker_fills_verified": False,
            "orders_enabled": False}
