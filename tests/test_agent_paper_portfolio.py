import copy
import unittest
from research.agent_paper_portfolio import initialize, transition, snapshot, verify


class AgentPaperPortfolioTests(unittest.TestCase):
    def test_independent_agents_and_round_trip(self):
        a = initialize("momentum-SPY", "SPY")
        b = initialize("reversal-SPY", "SPY")
        a = transition(a, target=1, execution_price=100, observed_at="2026-10-16T14:30:00Z")
        self.assertEqual(snapshot(a)["side"], "LONG")
        self.assertEqual(snapshot(b)["side"], "FLAT")
        self.assertAlmostEqual(snapshot(a)["equity"], 2000 / 1.001, places=6)
        a = transition(a, target=0, execution_price=110, observed_at="2026-10-19T14:30:00Z")
        self.assertEqual(snapshot(a)["side"], "FLAT")
        self.assertGreater(snapshot(a)["realized_pnl"], 0)
        self.assertEqual(len(a["events"]), 2)

    def test_hold_is_audited_without_fill(self):
        state = transition(initialize("trend-TLT", "TLT"), target=0,
                           execution_price=90, observed_at="2026-10-16T14:30:00Z")
        self.assertEqual(state["events"][0]["action"], "HOLD")
        self.assertFalse(snapshot(state)["broker_fills_verified"])

    def test_tampering_rejected(self):
        state = transition(initialize("a", "GLD"), target=1,
                           execution_price=100, observed_at="2026-10-16T14:30:00Z")
        corrupted = copy.deepcopy(state)
        corrupted["events"][0]["price"] = 200
        with self.assertRaises(ValueError):
            verify(corrupted)

    def test_invalid_price_and_target(self):
        state = initialize("a", "SPY")
        for target, price in [(2, 100), (1, -1), (1, float("nan"))]:
            with self.assertRaises(ValueError):
                transition(state, target=target, execution_price=price, observed_at="2026-10-16T14:30:00Z")


if __name__ == "__main__":
    unittest.main()
