import unittest
from research.agent_paper_portfolio import initialize, transition
from research.league_fixtures import MARKETS, STRATEGIES
from research.league_session_adapter import session_returns
from research.edge_session_calendar import session_bounds


def portfolios():
    return {m + "::" + s: initialize(m + "::" + s, m)
            for m in MARKETS for s in STRATEGIES}


def mark(portfolio, day, price=100):
    return transition(portfolio, target=0, execution_price=price,
                      observed_at=session_bounds(day)[0].isoformat())


class AdapterTests(unittest.TestCase):
    def test_consecutive_marks_produce_audited_open_to_open_observation(self):
        p = portfolios()
        agent = "SPY::tsmom_63"
        p[agent] = mark(mark(p[agent], "2026-10-16"), "2026-10-19")
        rows = session_returns(p)
        self.assertEqual(set(rows), {("2026-10-19", agent)})
        self.assertEqual(rows["2026-10-19", agent]["net_return_pct"], 0)
        self.assertTrue(rows["2026-10-19", agent]["not_intraday_day_trade"])

    def test_missing_intermediate_session_not_scored(self):
        p = portfolios()
        agent = "SPY::tsmom_63"
        p[agent] = mark(mark(p[agent], "2026-10-16"), "2026-10-20")
        self.assertEqual(session_returns(p), {})

    def test_tampered_hash_rejected(self):
        p = portfolios()
        agent = "SPY::tsmom_63"
        p[agent] = mark(p[agent], "2026-10-16")
        p[agent]["events"][0]["price"] = 999
        with self.assertRaises(ValueError):
            session_returns(p)

    def test_missing_agent_rejected(self):
        p = portfolios()
        del p["GLD::reversal_5"]
        with self.assertRaises(ValueError):
            session_returns(p)


if __name__ == "__main__":
    unittest.main()
