import unittest
from research.league_championships import championship_status


class ChampionshipDefinitionTests(unittest.TestCase):
    def test_no_intraday_winner_from_daily_evidence(self):
        status = championship_status()
        self.assertIsNone(status["first_profitable_day_trade"]["winner"])
        self.assertEqual(status["first_profitable_day_trade"]["status"],
                         "AWAITING_VERIFIED_INTRADAY_EVIDENCE")
        self.assertFalse(status["orders_enabled"])

    def test_no_automatic_season_winner(self):
        status = championship_status(season_complete=True)
        self.assertIsNone(status["most_profitable_season"]["winner"])
        self.assertEqual(status["most_profitable_season"]["status"],
                         "AWAITING_REVIEWED_SEASON_ADJUDICATION")

    def test_unreviewed_intraday_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            championship_status(intraday_evidence=[{"profit": 999999}])


if __name__ == "__main__":
    unittest.main()
