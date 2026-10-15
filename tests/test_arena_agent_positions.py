import copy
import unittest
from datetime import datetime, timezone
from research.agent_paper_portfolio import initialize, transition, snapshot
from research.arena_agent_positions import project
from research.edge_lab import IDS
from research.multi_market_observer import SYMBOLS

NOW = datetime(2026, 10, 19, 20, tzinfo=timezone.utc)


def source():
    rows = []
    for symbol in SYMBOLS:
        for sid in IDS:
            state = initialize(symbol + "::" + sid, symbol)
            state = transition(state, target=1 if sid == IDS[0] else 0,
                               execution_price=100, observed_at="2026-10-19T13:30:00+00:00")
            rows.append(snapshot(state))
    return {"schema": "oracle-q-agent-paper-positions-v1",
            "source_kind": "REPLAYED_AUDITED_FORWARD_LEDGER",
            "ledger_head_sha256": "a" * 64, "generated_at": NOW.isoformat(),
            "orders_enabled": False, "broker_fills_verified": False,
            "price_is_live": False, "edge_proven": False, "positions": rows}


class ProjectionTests(unittest.TestCase):
    def test_18_simulated_positions(self):
        data = project(source(), now=NOW)
        self.assertEqual(len(data["positions"]), 18)
        self.assertNotIn("portfolios", data)
        self.assertFalse(data["price_is_live"])

    def test_rejects_duplicate_agent(self):
        data = source()
        data["positions"][1] = copy.deepcopy(data["positions"][0])
        with self.assertRaises(ValueError):
            project(data, now=NOW)

    def test_rejects_false_equity(self):
        data = source()
        data["positions"][0]["equity"] += 500
        with self.assertRaises(ValueError):
            project(data, now=NOW)

    def test_rejects_live_claim(self):
        data = source()
        data["price_is_live"] = True
        with self.assertRaises(ValueError):
            project(data, now=NOW)


if __name__ == "__main__":
    unittest.main()
