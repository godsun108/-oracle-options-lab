"""Deterministic, no-broker paper portfolio state machine.

Positions are simulated at explicitly supplied execution prices; never claim
broker fills or real-time prices. Caller owns timestamp and source provenance.
"""
import copy
import hashlib
import json
import math

SCHEMA = "oracle-q-agent-paper-portfolio-v1"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def initialize(agent_id, symbol, *, cash=2000.0):
    if not isinstance(agent_id, str) or not agent_id or not isinstance(symbol, str) or not symbol:
        raise ValueError("agent identity and symbol required")
    if type(cash) not in (int, float) or not math.isfinite(cash) or cash <= 0:
        raise ValueError("invalid starting cash")
    state = {"schema": SCHEMA, "agent_id": agent_id, "symbol": symbol,
             "starting_cash": float(cash), "cash": float(cash), "quantity": 0.0,
             "average_entry": None, "realized_pnl": 0.0, "last_mark": None,
             "events": [], "head_sha256": None, "orders_enabled": False,
             "broker_fills_verified": False, "edge_proven": False}
    return state


def verify(state):
    if state.get("schema") != SCHEMA or any(state.get(k) is not False for k in
        ("orders_enabled", "broker_fills_verified", "edge_proven")):
        raise ValueError("invalid research-only portfolio")
    prior = None
    for event in state["events"]:
        body = {k: v for k, v in event.items() if k != "event_sha256"}
        if body["previous_sha256"] != prior or event["event_sha256"] != digest(body):
            raise ValueError("paper portfolio event chain corrupted")
        prior = event["event_sha256"]
    if state["head_sha256"] != prior:
        raise ValueError("paper portfolio head mismatch")
    return True


def transition(state, *, target, execution_price, observed_at, cost_bps=10):
    """Move between flat (0) and long (1), using a supplied *hypothetical* price.

    A 10bps fee/slippage assumption is charged on each traded notional.
    This is an accounting simulator, not a broker-paper execution adapter.
    """
    verify(state)
    if target not in (0, 1) or type(target) is not int:
        raise ValueError("only flat or long target supported")
    if type(execution_price) not in (int, float) or not math.isfinite(execution_price) or execution_price <= 0:
        raise ValueError("invalid execution price")
    if type(cost_bps) not in (int, float) or not math.isfinite(cost_bps) or not 0 <= cost_bps < 10000:
        raise ValueError("invalid costs")
    if not isinstance(observed_at, str) or not observed_at:
        raise ValueError("timestamp required")
    updated = copy.deepcopy(state)
    price = float(execution_price)
    fee = cost_bps / 10000
    quantity_before = updated["quantity"]
    action = "HOLD"
    if target == 1 and quantity_before == 0:
        qty = updated["cash"] / (price * (1 + fee))
        spent = qty * price
        updated["cash"] -= spent * (1 + fee)
        updated["quantity"] = qty
        updated["average_entry"] = price * (1 + fee)
        action = "SIMULATED_BUY"
    elif target == 0 and quantity_before > 0:
        proceeds = quantity_before * price * (1 - fee)
        updated["cash"] += proceeds
        updated["realized_pnl"] += proceeds - quantity_before * updated["average_entry"]
        updated["quantity"] = 0.0
        updated["average_entry"] = None
        action = "SIMULATED_SELL"
    updated["last_mark"] = {"price": price, "observed_at": observed_at}
    event = {"action": action, "target": target, "price": price, "observed_at": observed_at,
             "cost_bps": cost_bps, "quantity_after": updated["quantity"],
             "cash_after": updated["cash"], "previous_sha256": updated["head_sha256"]}
    event["event_sha256"] = digest(event)
    updated["events"].append(event)
    updated["head_sha256"] = event["event_sha256"]
    verify(updated)
    return updated


def snapshot(state):
    verify(state)
    mark = state["last_mark"]
    market_value = state["quantity"] * mark["price"] if mark else 0.0
    unrealized = state["quantity"] * (mark["price"] - state["average_entry"]) if state["quantity"] else 0.0
    return {"schema": "oracle-q-agent-paper-position-v1", "agent_id": state["agent_id"],
            "symbol": state["symbol"], "side": "LONG" if state["quantity"] else "FLAT",
            "quantity": state["quantity"], "average_entry": state["average_entry"],
            "cash": state["cash"], "market_value": market_value,
            "equity": state["cash"] + market_value, "realized_pnl": state["realized_pnl"],
            "unrealized_pnl": unrealized, "last_mark": mark,
            "event_count": len(state["events"]), "head_sha256": state["head_sha256"],
            "price_is_live": False, "broker_fills_verified": False,
            "orders_enabled": False, "edge_proven": False}
