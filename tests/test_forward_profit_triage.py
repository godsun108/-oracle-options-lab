import unittest
from research.forward_profit_triage import project
from research.league_fixtures import MARKETS, STRATEGIES


def scorecard():
    rows = []
    for m in MARKETS:
        for s in STRATEGIES:
            rows.append({"symbol": m, "strategy_id": s,
                         "outcomes_observed": 0, "paired_benchmark_observations": 0,
                         "mean_hypothetical_return_pct": None,
                         "mean_excess_vs_buy_hold_pct": None,
                         "positive_observations": 0})
    return {"schema": "oracle-q-edge-forward-scorecard-v1",
            "status": "FORWARD_PAPER_RESEARCH_ONLY",
            "orders_enabled": False, "fill_verified": False,
            "edge_proven": False, "eligible_for_live_trading": False,
            "pairs": rows}


class ProfitTriageTests(unittest.TestCase):
    def test_zero_outcomes_never_becomes_profit(self):
        result = project(scorecard())
        self.assertEqual(result["agents_with_positive_observed_mean"], 0)
        self.assertFalse(result["winner_certified"])

    def test_observed_positive_is_not_proven_edge(self):
        source = scorecard()
        p = source["pairs"][0]
        p.update(outcomes_observed=2, paired_benchmark_observations=2,
                 mean_hypothetical_return_pct=0.25,
                 mean_excess_vs_buy_hold_pct=-0.15,
                 positive_observations=1)
        result = project(source)
        self.assertEqual(result["agents_with_positive_observed_mean"], 1)
        self.assertEqual(result["agents_with_positive_observed_excess"], 0)
        self.assertFalse(result["candidates"][0]["edge_proven"])

    def test_incomplete_benchmark_is_not_positive_excess(self):
        source = scorecard()
        source["pairs"][0].update(outcomes_observed=2,
            paired_benchmark_observations=1, mean_hypothetical_return_pct=0.3)
        result = project(source)
        self.assertIsNone(result["candidates"][0]["mean_excess_vs_buy_hold_pct"])

    def test_unsafe_flags_rejected(self):
        source = scorecard()
        source["edge_proven"] = True
        with self.assertRaises(ValueError):
            project(source)


if __name__ == "__main__":
    unittest.main()
