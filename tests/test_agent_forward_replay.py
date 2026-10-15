import unittest
from datetime import datetime, timezone
from research.agent_forward_replay import replay
from research.edge_forward_paper import digest
from research.edge_session_calendar import session_bounds


def ledger(events):
    prior = None
    result = []
    for event in events:
        e = dict(event, previous_sha256=prior)
        e["event_sha256"] = digest(e)
        prior = e["event_sha256"]
        result.append(e)
    return {"schema": "oracle-q-edge-forward-paper-v1", "orders_enabled": False,
            "events": result, "events_recorded": len(result), "head_sha256": prior}


def signal(date, registered, target):
    return {"type": "SIGNAL_REGISTERED", "symbol": "SPY",
            "strategy_id": "tsmom_63", "signal_date": date,
            "registered_at": registered, "signal": target}


def opening(date, price):
    return {"type": "SOURCE_OPEN_CHECKPOINT", "symbol": "SPY",
            "open_date": date, "open_price": price}


class ReplayTests(unittest.TestCase):
    def test_prospective_buy_hold_and_sell(self):
        data = ledger([
            signal("2026-10-15", "2026-10-15T22:00:00+00:00", 1),
            opening("2026-10-16", 100),
            signal("2026-10-16", "2026-10-16T22:00:00+00:00", 0),
            opening("2026-10-19", 110)])
        result = replay(data)
        self.assertEqual(len(result["positions"]), 18)
        row = next(p for p in result["positions"] if p["agent_id"] == "SPY::tsmom_63")
        self.assertEqual(row["side"], "FLAT")
        self.assertGreater(row["realized_pnl"], 0)
        self.assertFalse(result["broker_fills_verified"])

    def test_late_registration_cannot_buy_at_past_open(self):
        data = ledger([
            signal("2026-10-15", "2026-10-16T18:00:00+00:00", 1),
            opening("2026-10-16", 100)])
        row = next(p for p in replay(data)["positions"] if p["agent_id"] == "SPY::tsmom_63")
        self.assertEqual(row["side"], "FLAT")

    def test_legacy_untimed_signal_never_opens_position(self):
        old = signal("2026-10-15", "2026-10-15T22:00:00+00:00", 1)
        del old["registered_at"]
        data = ledger([old, opening("2026-10-16", 100)])
        row = next(p for p in replay(data)["positions"] if p["agent_id"] == "SPY::tsmom_63")
        self.assertEqual(row["side"], "FLAT")
        self.assertEqual(row["realized_pnl"], 0)

    def test_tampering_rejected(self):
        data = ledger([opening("2026-10-16", 100)])
        data["events"][0]["open_price"] = 999
        with self.assertRaises(ValueError):
            replay(data)


if __name__ == "__main__":
    unittest.main()
