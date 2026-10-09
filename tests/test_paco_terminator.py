import unittest
from research.paco_terminator import evaluate

NOW="2026-10-09T09:30:00-04:00"
POS=[{"symbol":"SPY_P","quantity":2,"entry_ask":1.35}]
def quote(**kwargs):
    x={"SPY_P":{"bid":5.0,"ask":5.10,"age_seconds":0.2,"bid_size":3}}
    x["SPY_P"].update(kwargs)
    return x

class PACOTests(unittest.TestCase):
    def test_partial_exit_scenarios(self):
        p=evaluate(POS,quote(),now_iso=NOW)
        x=p["positions"][0]
        self.assertFalse(p["orders_enabled"])
        self.assertTrue(p["human_decision_required"])
        self.assertIn(100,x["thresholds_crossed"])
        self.assertEqual([a["sell_contracts"] for a in x["scenarios"]],[0,1,2])
        self.assertFalse(x["cancelled_orders_verified"])
    def test_no_quote_no_execution(self):
        p=evaluate(POS,{},now_iso=NOW)
        self.assertEqual(p["positions"][0]["status"],"NO_QUOTE")
    def test_stale_quote_rejected(self):
        p=evaluate(POS,quote(age_seconds=60),now_iso=NOW)
        self.assertEqual(p["positions"][0]["status"],"UNRELIABLE_QUOTE")
    def test_no_naive_fill_beyond_size(self):
        p=evaluate(POS,quote(bid_size=1),now_iso=NOW)
        self.assertEqual([a["sell_contracts"] for a in p["positions"][0]["scenarios"]],[0,1])
    def test_invalid_position_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([{"symbol":"SPY_P","quantity":0,"entry_ask":1.35}],quote(),now_iso=NOW)
if __name__=="__main__":
    unittest.main()
