"""Replay independently registered prospective signals into 18 paper accounts.

Historical source opens are *hypothetical* execution marks, never broker fills.
Only a signal registered strictly before its next entry open can be executed.
State is deterministically reconstructed from the full verified forward ledger.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from research.agent_paper_portfolio import initialize, transition, snapshot
from research.edge_forward_paper import verify, parse_utc_timestamp
from research.edge_session_calendar import session_bounds, next_session
from research.edge_lab import IDS
from research.multi_market_observer import SYMBOLS


def replay(ledger):
    events = verify(ledger)
    opens = {}
    signals = {}
    for event in events:
        if event["type"] == "SOURCE_OPEN_CHECKPOINT":
            key = event["symbol"], event["open_date"]
            if key in opens:
                raise ValueError("duplicate opening-price checkpoint")
            opens[key] = event["open_price"]
        elif event["type"] == "SIGNAL_REGISTERED":
            key = event["symbol"], event["strategy_id"], event["signal_date"]
            if key in signals:
                raise ValueError("duplicate signal")
            signals[key] = event
    states = {}
    rows = []
    for symbol in SYMBOLS:
        for sid in IDS:
            agent = symbol + "::" + sid
            state = initialize(agent, symbol)
            pending = []
            for (sym, strategy, signal_day), signal in signals.items():
                if (sym, strategy) != (symbol, sid):
                    continue
                if signal.get("signal") not in (0, 1) or type(signal["signal"]) is not int:
                    raise ValueError("invalid target")
                # Legacy ledger records can be hash-valid yet lack a trustworthy\n                # registration timestamp. Exclude them from portfolio execution.\n                if not signal.get("registered_at"):\n                    continue\n                registered = parse_utc_timestamp(signal["registered_at"])
                entry = next_session(signal_day)
                entry_open = session_bounds(entry)[0]
                if registered >= entry_open:
                    # Late signals must not acquire retroactive paper fills.
                    continue
                pending.append((entry, registered, signal_day, signal["signal"]))
            for entry, registered, signal_day, target in sorted(pending):
                price = opens.get((symbol, entry))
                if price is None:
                    continue
                observed = session_bounds(entry)[0].isoformat()
                state = transition(state, target=target, execution_price=price,
                                   observed_at=observed, cost_bps=10)
            # Mark-to-market at most recent available checkpoint, but do not
            # silently claim a price was known before its session opened.
            available = sorted((day, price) for (sym, day), price in opens.items() if sym == symbol)
            if available:
                day, price = available[-1]
                mark_time = session_bounds(day)[0].isoformat()
                last = state["last_mark"]
                if last is None or parse_utc_timestamp(mark_time) > parse_utc_timestamp(last["observed_at"]):
                    state = transition(state, target=1 if state["quantity"] else 0,
                                       execution_price=price, observed_at=mark_time, cost_bps=10)
            states[agent] = state
            rows.append(snapshot(state))
    return {"schema": "oracle-q-agent-paper-positions-v1",
            "source_kind": "REPLAYED_AUDITED_FORWARD_LEDGER",
            "ledger_head_sha256": ledger["head_sha256"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "orders_enabled": False, "broker_fills_verified": False,
            "price_is_live": False, "edge_proven": False,
            "positions": rows, "portfolios": states,
            "warning": "Historical open checkpoints are replayed only after prospectively registered signals. Prices and fills are hypothetical, not real-time or broker confirmed."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = replay(json.loads(Path(args.ledger).read_text()))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
