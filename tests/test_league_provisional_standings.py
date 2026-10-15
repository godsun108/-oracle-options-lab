import unittest
from research.agent_paper_portfolio import initialize, transition
from research.edge_session_calendar import session_bounds
from research.league_fixtures import MARKETS, STRATEGIES
from research.league_provisional_standings import project


def portfolio_set(missing=None):
    portfolios = {}
    for market in MARKETS:
        for strategy in STRATEGIES:
            agent = market + "::" + strategy
            state = initialize(agent, market)
            days = ["2026-10-16", "2026-10-19"]
            if agent == missing:
                days = days[:1]
            for day in days:
                state = transition(state, target=0, execution_price=100,
                                   observed_at=session_bounds(day)[0].isoformat())
            portfolios[agent] = state
    return portfolios


class ProvisionalStandingsTests(unittest.TestCase):
    def test_complete_session_has_six_duels_and_six_crowns(self):
        result = project(portfolio_set(), ["2026-10-19"])
        self.assertEqual(result["included_complete_sessions"], ["2026-10-19"])
        self.assertEqual(len(result["daily"][0]["duels"]), 6)
        self.assertEqual(len(result["daily"][0]["market_crowns"]), 6)
        self.assertTrue(all(c["winner"] is None for c in result["daily"][0]["market_crowns"]))
        self.assertFalse(result["official_points_awarded"])
        self.assertFalse(result["day_trade_winners_declared"])

    def test_missing_agent_excludes_whole_session(self):
        result = project(portfolio_set("GLD::reversal_5"), ["2026-10-19"])
        self.assertEqual(result["included_complete_sessions"], [])
        self.assertEqual(result["excluded_incomplete_sessions"], ["2026-10-19"])
        self.assertIsNone(result["comparable_market_returns"])

    def test_invalid_session_order_rejected(self):
        with self.assertRaises(ValueError):
            project(portfolio_set(), ["2026-10-19", "2026-10-19"])


if __name__ == "__main__":
    unittest.main()
