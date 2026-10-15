import unittest
from research.arena_feed import arena_feed

def scorecard():
    return {"schema":"oracle-q-shadow-league-score-v1","orders_enabled":False,
            "promotion_authorized":False,"rows":[{
            "candidate_id":"SPY-v1","market":"SPY","status":"INCOMPLETE_EVIDENCE",
            "missing_windows":["w1"],"net_profit_usd":None,"net_return_pct":None,
            "first_positive_window":None,"max_drawdown_pct":None,
            "edge_proven":False,"eligible_for_live_trading":False}]}
class ArenaFeedTests(unittest.TestCase):
    def test_incomplete_is_not_erased_or_claimed_live(self):
        result=arena_feed(scorecard(),generated_at="2026-10-14T21:00:00Z")
        self.assertEqual(len(result["rows"]),1)
        self.assertIsNone(result["rows"][0]["net_return_pct"])
        self.assertFalse(result["live"])
    def test_rejects_execution_flag(self):
        data=scorecard();data["orders_enabled"]=True
        with self.assertRaises(ValueError):
            arena_feed(data,generated_at="2026-10-14T21:00:00Z")
    def test_rejects_fake_proof(self):
        data=scorecard();data["rows"][0]["edge_proven"]=True
        with self.assertRaises(ValueError):
            arena_feed(data,generated_at="2026-10-14T21:00:00Z")
    def test_rejects_naive_timestamp(self):
        with self.assertRaises(ValueError):
            arena_feed(scorecard(),generated_at="2026-10-14T21:00:00")
if __name__=="__main__":
    unittest.main()
