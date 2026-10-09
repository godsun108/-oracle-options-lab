import unittest
from datetime import date,timedelta
from research.spx_ath_spy_puts import signal

def bars():
    start=date(2025,1,1)
    return [{"date":(start+timedelta(days=i)).isoformat(),"close":100+i/10} for i in range(253)]

class ATHTests(unittest.TestCase):
    def test_record_close_and_expiration_window(self):
        data=bars()
        day=data[-1]["date"]
        expiration=(date.fromisoformat(day)+timedelta(days=45)).isoformat()
        contracts=[{"symbol":"SPY_TEST_PUT","type":"put","expiration":expiration,"strike":110,"bid":2,"ask":2.2},
                   {"symbol":"SPY_TEST_CALL","type":"call","expiration":expiration,"strike":110,"bid":2,"ask":2.2}]
        out=signal(data,contracts,as_of=day)
        self.assertTrue(out["spx_record_close"])
        self.assertEqual(len(out["candidates"]),1)
        self.assertFalse(out["orders_enabled"])
    def test_no_record_no_trade(self):
        data=bars()
        data[-1]["close"]=99
        out=signal(data,[],as_of=data[-1]["date"])
        self.assertEqual(out["status"],"NO_SIGNAL")
    def test_no_short_history(self):
        data=bars()[:30]
        self.assertEqual(signal(data,[],as_of=data[-1]["date"])["status"],"INSUFFICIENT_HISTORY")
    def test_no_future_leakage(self):
        data=bars()
        out=signal(data,[],as_of=data[-2]["date"])
        self.assertEqual(out["status"],"CANDIDATES_REQUIRE_HISTORICAL_OPTION_QUOTES")
if __name__=="__main__":
    unittest.main()
