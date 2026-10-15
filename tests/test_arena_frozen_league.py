from unittest.mock import patch
import unittest
from research.arena_frozen_league import frozen_league_arena

def season(status="ACCUMULATING_FORWARD_EVIDENCE"):
    return {"schema":"oracle-q-paper-league-v1","orders_enabled":False,
            "season_id":"frozen-test","as_of":"2026-10-15T12:00:00+00:00",
            "ledger_head_sha256":"a"*64,"rules_sha256":"b"*64,
            "teams":[{"team":"SPY","status":status,
                      "completed_common_sessions":1,"required_sessions":60,
                      "missing_eligible_windows":[],"net_return_pct":999,
                      "max_drawdown_pct":-5}]}
class FrozenArenaTests(unittest.TestCase):
    @patch("research.arena_frozen_league.standings")
    def test_partial_results_never_rank(self, scorer):
        scorer.return_value=season()
        result=frozen_league_arena({},as_of="2026-10-15T12:00:00Z")
        self.assertIsNone(result["rows"][0]["net_return_pct"])
        self.assertFalse(result["live"])
    @patch("research.arena_frozen_league.standings")
    def test_reject_premature_completed_claim(self, scorer):
        scorer.return_value=season("FIXED_WINDOW_DESCRIPTIVE_RESULT")
        with self.assertRaises(ValueError):
            frozen_league_arena({},as_of="2026-10-15T12:00:00Z")
    @patch("research.arena_frozen_league.standings")
    def test_rejects_orders(self, scorer):
        data=season();data["orders_enabled"]=True;scorer.return_value=data
        with self.assertRaises(ValueError):
            frozen_league_arena({},as_of="2026-10-15T12:00:00Z")
if __name__=="__main__":
    unittest.main()
