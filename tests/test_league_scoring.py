import unittest
from research.league_scoring import daily_duel, daily_crown, weekly_market_returns
from research.league_fixtures import MARKETS, STRATEGIES


def row(session, agent, value):
    return {"session": session, "agent_id": agent, "net_return_pct": value,
            "audited": True, "complete": True, "orders_enabled": False,
            "broker_fills_verified": False}


class ScoringTests(unittest.TestCase):
    def test_duel_can_win_while_both_lose_without_profitable_claim(self):
        a, b = "SPY::tsmom_63", "SPY::trend_200"
        match = daily_duel("2026-10-16", a, b,
                           {a: row("2026-10-16", a, -1), b: row("2026-10-16", b, -2)})
        self.assertEqual(match["winner"], a)
        self.assertFalse(match["profitable_winner"])
        self.assertEqual(match["points"][a], 1)

    def test_crown_requires_positive_unique_leader(self):
        names = ["SPY::" + s for s in STRATEGIES]
        evidence = {a: row("2026-10-16", a, v)
                    for a, v in zip(names, [-1, -2, -3])}
        self.assertIsNone(daily_crown("2026-10-16", "SPY", evidence)["winner"])
        evidence[names[0]]["net_return_pct"] = 2
        self.assertEqual(daily_crown("2026-10-16", "SPY", evidence)["winner"], names[0])
        evidence[names[1]]["net_return_pct"] = 2
        self.assertIsNone(daily_crown("2026-10-16", "SPY", evidence)["winner"])

    def test_weekly_market_cup_requires_all_eighteen_per_session(self):
        session = "2026-10-16"
        evidence = {(session, m + "::" + s): row(session, m + "::" + s, 1 if m == "SPY" else 0)
                    for m in MARKETS for s in STRATEGIES}
        result = weekly_market_returns([session], evidence)
        self.assertEqual(result["winner"], "SPY")
        self.assertAlmostEqual(result["market_net_return_pct"]["SPY"], 1)
        del evidence[(session, "GLD::reversal_5")]
        with self.assertRaises(ValueError):
            weekly_market_returns([session], evidence)

    def test_unverified_data_never_scores(self):
        a, b = "SPY::tsmom_63", "SPY::trend_200"
        evidence = {a: row("2026-10-16", a, 5), b: row("2026-10-16", b, 2)}
        evidence[a]["audited"] = False
        with self.assertRaises(ValueError):
            daily_duel("2026-10-16", a, b, evidence)


if __name__ == "__main__":
    unittest.main()
