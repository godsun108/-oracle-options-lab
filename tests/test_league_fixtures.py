import unittest
from research.league_fixtures import league_plan, round_robin


class FixtureTests(unittest.TestCase):
    def test_every_market_has_three_unique_internal_duels(self):
        plan = league_plan()
        self.assertEqual(len(plan["daily_within_market_rotation"]), 6)
        for market, fixtures in plan["daily_within_market_rotation"].items():
            self.assertEqual(len(fixtures), 3)
            self.assertEqual(len({tuple(f) for f in fixtures}), 3)
            self.assertTrue(all(a.startswith(market + "::") and b.startswith(market + "::")
                                for a, b in fixtures))

    def test_weekly_market_rotation_has_all_fifteen_pairs(self):
        self.assertEqual(len(league_plan()["weekly_cross_market_rotation"]), 15)

    def test_no_fabricated_winners(self):
        plan = league_plan()
        self.assertFalse(plan["winners_declared"])
        self.assertFalse(plan["orders_enabled"])
        self.assertEqual(plan["status"], "DESIGN_ONLY_NOT_REGISTERED")

    def test_duplicate_competitors_rejected(self):
        with self.assertRaises(ValueError):
            round_robin(["SPY", "SPY"])


if __name__ == "__main__":
    unittest.main()
