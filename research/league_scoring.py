"""Evidence-gated, deterministic hypothetical return scoring.

This does not change registered season rules or infer returns from daily prices.
Only caller-supplied audited, complete and same-window observations can score.
"""
import math

from research.league_fixtures import MARKETS, STRATEGIES


def _check(row, *, session, agent):
    if not isinstance(row, dict) or row.get("agent_id") != agent or row.get("session") != session:
        raise ValueError("missing or mismatched session evidence")
    if row.get("audited") is not True or row.get("complete") is not True:
        raise ValueError("unverified or incomplete session evidence")
    if any(row.get(flag) is not False for flag in ("orders_enabled", "broker_fills_verified")):
        raise ValueError("non-paper evidence rejected")
    value = row.get("net_return_pct")
    if type(value) not in (float, int) or not math.isfinite(value) or value <= -100:
        raise ValueError("invalid net return")
    return float(value)


def daily_duel(session, left, right, evidence):
    """Winner gets one match point; draws get none; no positive-profit claim for losses."""
    if left == right or left.split("::")[0] != right.split("::")[0]:
        raise ValueError("daily duel must be between different agents in one market")
    if left.split("::")[0] not in MARKETS or any(
        a.split("::")[-1] not in STRATEGIES for a in (left, right)
    ):
        raise ValueError("unregistered competitor")
    a = _check(evidence.get(left), session=session, agent=left)
    b = _check(evidence.get(right), session=session, agent=right)
    winner = left if a > b else right if b > a else None
    return {"session": session, "agents": [left, right], "winner": winner,
            "points": {left: int(winner == left), right: int(winner == right)},
            "net_return_pct": {left: a, right: b},
            "profitable_winner": bool(winner and max(a, b) > 0),
            "orders_enabled": False, "edge_proven": False}


def daily_crown(session, market, evidence):
    """Only strictly positive best net return wins; tied leaders get no crown."""
    if market not in MARKETS:
        raise ValueError("unknown market")
    values = {market + "::" + s: _check(evidence.get(market + "::" + s),
              session=session, agent=market + "::" + s) for s in STRATEGIES}
    best = max(values.values())
    winners = [a for a, value in values.items() if value == best]
    winner = winners[0] if best > 0 and len(winners) == 1 else None
    return {"session": session, "market": market, "winner": winner,
            "bonus_points": {a: int(a == winner) for a in values},
            "net_return_pct": values, "orders_enabled": False, "edge_proven": False}


def weekly_market_returns(sessions, evidence):
    """Equal-weight each market's three sleeves, then compound common sessions."""
    if not sessions or len(sessions) != len(set(sessions)):
        raise ValueError("unique common sessions required")
    result = {}
    for market in MARKETS:
        equity = 1.0
        for session in sessions:
            values = [_check(evidence.get((session, market + "::" + s)),
                      session=session, agent=market + "::" + s) for s in STRATEGIES]
            equity *= 1 + sum(values) / len(values) / 100
        result[market] = (equity - 1) * 100
    return {"sessions": list(sessions), "market_net_return_pct": result,
            "winner": max(result, key=result.get) if len(set(result.values())) == len(result) else None,
            "orders_enabled": False, "edge_proven": False}
