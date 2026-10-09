import unittest
from research.cash_observation_ledger import append
from research.cash_progress_report import report
from tests.test_cash_observation_ledger import baseline

class ProgressTests(unittest.TestCase):
    def test_one_day_is_not_multiday(self):
        x=report(append(None,baseline()))
        self.assertFalse(x["multi_day_continuity_observed"])
        self.assertFalse(x["strategy_performance_available"])
        self.assertEqual(x["distinct_trading_dates"],1)
    def test_two_distinct_days(self):
        a=append(None,baseline())
        b=append(a,baseline("2026-10-09","b"*64))
        x=report(b)
        self.assertTrue(x["multi_day_continuity_observed"])
        self.assertEqual(x["distinct_trading_dates"],2)
        self.assertEqual(x["trades"],0)
    def test_tamper_rejected(self):
        a=append(None,baseline())
        a["entries"][0]["as_of"]="2026-01-01"
        with self.assertRaises(ValueError):
            report(a)
if __name__=="__main__":
    unittest.main()
