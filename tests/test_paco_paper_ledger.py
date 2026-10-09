import unittest
from research.paco_paper_ledger import initial,record,verify

Q={"bid":1.3,"ask":1.35,"age_seconds":0.1,"bid_size":10,"ask_size":10}
T1="2026-10-09T09:30:01-04:00"
T2="2026-10-09T09:30:02-04:00"
class PACOLedgerTests(unittest.TestCase):
    def test_buy_sell_and_verify(self):
        a=record(initial(),symbol="SPY_TEST",side="BUY",quantity=2,quote=Q,as_of=T1)
        b=record(a,symbol="SPY_TEST",side="SELL",quantity=1,quote=Q,as_of=T2)
        self.assertEqual(b["positions"],{"SPY_TEST":1})
        self.assertTrue(verify(b)["verified"])
        self.assertFalse(verify(b)["performance_established"])
    def test_no_unheld_sell(self):
        with self.assertRaises(ValueError):
            record(initial(),symbol="SPY_TEST",side="SELL",quantity=1,quote=Q,as_of=T1)
    def test_no_fake_size(self):
        with self.assertRaises(ValueError):
            record(initial(),symbol="SPY_TEST",side="BUY",quantity=11,quote=Q,as_of=T1)
    def test_no_overspending(self):
        with self.assertRaises(ValueError):
            record(initial(100),symbol="SPY_TEST",side="BUY",quantity=1,quote=Q,as_of=T1)
    def test_tamper_detected(self):
        a=record(initial(),symbol="SPY_TEST",side="BUY",quantity=1,quote=Q,as_of=T1)
        a["entries"][0]["price"]=0.01
        with self.assertRaises(ValueError):verify(a)
    def test_stale_quote_rejected(self):
        with self.assertRaises(ValueError):
            record(initial(),symbol="SPY_TEST",side="BUY",quantity=1,
                   quote={**Q,"age_seconds":30},as_of=T1)
if __name__=="__main__":unittest.main()
