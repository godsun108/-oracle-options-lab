import unittest
from research.daily_focus import rank

class DailyFocusTests(unittest.TestCase):
    def test_rank_and_no_trade(self):
        p={"cutoff":"2026-10-08","results":[
            {"symbol":"SPY","status":"OBSERVATION_ONLY","bars":250,"as_of":"2026-10-08","ret5":0.02,"above_ma200":True},
            {"symbol":"GLD","status":"OBSERVATION_ONLY","bars":250,"as_of":"2026-10-08","ret5":-0.05,"above_ma200":False},
            {"symbol":"TLT","status":"OBSERVATION_ONLY","bars":250,"as_of":"2026-10-07","ret5":0.9,"above_ma200":True}]}
        r=rank(p)
        self.assertEqual([x["symbol"] for x in r["ranking"]],["GLD","SPY"])
        self.assertEqual(r["recommended_action"],"NO_TRADE")
        self.assertFalse(r["paper_orders_enabled"])
    def test_empty(self):
        r=rank({"cutoff":"2026-10-08","results":[]})
        self.assertEqual(r["ranking"],[])
        self.assertEqual(r["recommended_action"],"NO_TRADE")

if __name__=="__main__":
    unittest.main()
