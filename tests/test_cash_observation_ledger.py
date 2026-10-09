import copy
import unittest
from research.cash_observation_ledger import append

def baseline(day="2026-10-08",source="a"*64):
    return {"schema":"oracle-q-cash-baseline-v1","status":"NO_TRADE_CASH_BASELINE",
            "orders_enabled":False,"strategy_enabled":False,"trades":0,
            "initial_cash":2000.0,"ending_cash":2000.0,"return_pct":0.0,
            "realized_pnl":0.0,"unrealized_pnl":0.0,"as_of":day,"source_sha256":source}
class LedgerTests(unittest.TestCase):
    def test_append_and_idempotency(self):
        one=append(None,baseline())
        self.assertEqual(append(one,baseline()),one)
        two=append(one,baseline("2026-10-09","b"*64))
        self.assertEqual(len(two["entries"]),2)
        self.assertEqual(two["entries"][1]["previous_hash"],one["entries"][0]["entry_hash"])
    def test_tampering_rejected(self):
        one=append(None,baseline())
        one["entries"][0]["cash"]=99999
        with self.assertRaises(ValueError):
            append(one,baseline("2026-10-09","b"*64))
    def test_conflicting_same_day_rejected(self):
        one=append(None,baseline())
        with self.assertRaises(ValueError):
            append(one,baseline(source="b"*64))
    def test_time_regression_rejected(self):
        one=append(None,baseline())
        with self.assertRaises(ValueError):
            append(one,baseline("2026-10-07","b"*64))
    def test_trades_rejected(self):
        b=baseline()
        b["trades"]=1
        with self.assertRaises(ValueError):
            append(None,b)
if __name__=="__main__":
    unittest.main()
