import unittest
from research.feed_run_summary import summary

class FeedRunSummaryTests(unittest.TestCase):
    def test_pass_does_not_claim_profit(self):
        result=summary({"status":"PASS","observed":6,"expected":6,"problems":[]})
        self.assertIn("Evidence gate:** PASS",result)
        self.assertIn("not evidence of strategy profitability",result)
    def test_fail_displays_problems(self):
        result=summary({"status":"FAIL","problems":["SPY:NOT_OBSERVED"]})
        self.assertIn("SPY:NOT_OBSERVED",result)
        self.assertIn("Evidence gate:** FAIL",result)
    def test_missing_status_fails_closed(self):
        self.assertIn("Evidence gate:** FAIL",summary({}))
if __name__=="__main__":
    unittest.main()
