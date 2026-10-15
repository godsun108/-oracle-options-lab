import unittest
from research.agent_paper_portfolio import initialize, transition
from research.edge_session_calendar import session_bounds
from research.league_fixtures import MARKETS, STRATEGIES
from research.league_readiness_report import report


def source(days, missing=None):
    portfolios = {}
    for market in MARKETS:
        for strategy in STRATEGIES:
            agent = market + "::" + strategy
            state = initialize(agent, market)
            for day in (days[:-1] if agent == missing else days):
                state = transition(state, target=0, execution_price=100,
                                   observed_at=session_bounds(day)[0].isoformat())
            portfolios[agent] = state
    return {"schema": "oracle-q-agent-paper-positions-v1",
            "source_kind": "REPLAYED_AUDITED_FORWARD_LEDGER",
            "orders_enabled": False, "broker_fills_verified": False,
            "price_is_live": False, "edge_proven": False,
            "portfolios": portfolios}


class ReadinessReportTests(unittest.TestCase):
    def test_two_consecutive_open_dates_yield_six_provisional_duels(self):
        result = report(source(["2026-10-16", "2026-10-19"]))
        self.assertEqual(result["complete_session_count"], 1)
        self.assertEqual(result["daily_matches_eligible_for_provisional_scoring"], 6)
        self.assertFalse(result["official_points_awarded"])

    def test_missing_one_agent_excludes_day(self):
        result = report(source(["2026-10-16", "2026-10-19"], "GLD::reversal_5"))
        self.assertEqual(result["complete_session_count"], 0)
        self.assertEqual(result["daily_matches_eligible_for_provisional_scoring"], 0)

    def test_no_marks_is_explicit_not_zero_profit(self):
        result = report(source([]))
        self.assertEqual(result["status"], "NO_OBSERVED_OPEN_CHECKPOINTS")

    def test_unsafe_source_rejected(self):
        data = source([])
        data["orders_enabled"] = True
        with self.assertRaises(ValueError):
            report(data)


if __name__ == "__main__":
    unittest.main()
