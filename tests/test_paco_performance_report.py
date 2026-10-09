import unittest
from research.paco_paper_ledger import initial,record
from research.paco_performance_report import report
Q={"bid":1.30,"ask":1.35,"age_seconds":0.1,"bid_size":10,"ask_size":10}
T1="2026-10-09T09:30:01-04:00"
T2="2026-10-09T09:30:02-04:00"
class PerformanceTests(unittest.TestCase):
    def test_empty_baseline(self):
        r=report(initial())
        self.assertEqual(r["hypothetical_total_pnl"],0)
        self.assertFalse(r["historical_edge_established"])
    def test_realized_and_unrealized(self):
        x=record(initial(),symbol="SPY_P",side="BUY",quantity=2,quote=Q,as_of=T1)
        x=record(x,symbol="SPY_P",side="SELL",quantity=1,
                 quote={**Q,"bid":5.0,"ask":5.1},as_of=T2)
        r=report(x,{"SPY_P":{"bid":5.0,"age_seconds":0.1,"bid_size":2}})
        self.assertEqual(r["closed_contracts"],1)
        self.assertGreater(r["hypothetical_realized_pnl"],0)
        self.assertGreater(r["hypothetical_unrealized_pnl"],0)
        self.assertTrue(r["all_positions_marked"])
        self.assertFalse(r["live_performance_established"])
    def test_missing_marks_no_total(self):
        x=record(initial(),symbol="SPY_P",side="BUY",quantity=1,quote=Q,as_of=T1)
        r=report(x)
        self.assertIsNone(r["hypothetical_total_pnl"])
        self.assertEqual(r["unmarked_symbols"],["SPY_P"])
    def test_tampering_rejected(self):
        x=record(initial(),symbol="SPY_P",side="BUY",quantity=1,quote=Q,as_of=T1)
        x["entries"][0]["quantity"]=2
        with self.assertRaises(ValueError):report(x)
if __name__=="__main__":unittest.main()
