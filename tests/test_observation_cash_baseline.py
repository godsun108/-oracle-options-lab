import unittest
from research.observation_cash_baseline import build_baseline
from tests.test_feed_evidence import fixture, NOW

class CashBaselineTests(unittest.TestCase):
    def test_verified_observation_no_trade(self):
        report=build_baseline(fixture(),now=NOW)
        self.assertEqual(report["trades"],0)
        self.assertEqual(report["initial_cash"],report["ending_cash"])
        self.assertFalse(report["orders_enabled"])
        self.assertFalse(report["strategy_enabled"])
    def test_rejects_modified_observation(self):
        payload=fixture()
        payload["results"][0]["as_of"]="2020-01-01"
        with self.assertRaises(ValueError):
            build_baseline(payload,now=NOW)
    def test_rejects_bad_cash(self):
        with self.assertRaises(ValueError):
            build_baseline(fixture(),now=NOW,starting_cash=-1)
if __name__=="__main__":
    unittest.main()
