import copy
import unittest

from research.agent_paper_portfolio import initialize, transition
from research.agent_equity_history import equity_history


class EquityHistoryTests(unittest.TestCase):
    def test_empty_history(self):
        result = equity_history(initialize("SPY::test", "SPY"))
        self.assertEqual(result["points"], [])
        self.assertEqual(result["max_observed_drawdown_pct"], 0.0)
        self.assertFalse(result["edge_proven"])

    def test_observed_marks_and_drawdown(self):
        state = initialize("SPY::test", "SPY")
        for target, price, day in [(1, 100, "2026-10-01T13:30:00+00:00"),
                                   (1, 90, "2026-10-02T13:30:00+00:00"),
                                   (0, 95, "2026-10-05T13:30:00+00:00")]:
            state = transition(state, target=target, execution_price=price,
                               observed_at=day)
        result = equity_history(state)
        self.assertEqual(len(result["points"]), 3)
        self.assertLess(result["max_observed_drawdown_pct"], 0)
        self.assertAlmostEqual(result["points"][-1]["equity"], state["cash"])
        self.assertEqual(result["points"][-1]["event_sha256"], state["head_sha256"])

    def test_tampering_rejected(self):
        state = transition(initialize("SPY::test", "SPY"), target=1,
                           execution_price=100, observed_at="2026-10-01T13:30:00+00:00")
        bad = copy.deepcopy(state)
        bad["cash"] += 5
        with self.assertRaises(ValueError):
            equity_history(bad)


if __name__ == "__main__":
    unittest.main()
