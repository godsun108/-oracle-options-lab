import unittest
from research.paco_premium_comparison import compare

def sample(bid,ask,when="2026-10-09T00:00:00Z"):
    return {"status":"COLLECTED","orders_enabled":False,"collected_at":when,"snapshots":[{"provider":"tradier","orders_enabled":False,"contracts":[{"occ_symbol":"SPY261120P00600000","type":"put","expiration":"2026-11-20","strike":600,"bid":bid,"ask":ask}]}]}

class PremiumComparisonTests(unittest.TestCase):
    def test_midpoint_and_conservative_spread(self):
        r=compare(sample(2,2.4),sample(2.5,2.9,"2026-10-10T00:00:00Z"))
        self.assertEqual(r["matched_contracts"],1)
        self.assertAlmostEqual(r["contracts"][0]["midpoint_change"],.5)
        self.assertAlmostEqual(r["contracts"][0]["hypothetical_buy_ask_sell_bid_change"],.1)
        self.assertFalse(r["contracts"][0]["executable_fill_verified"])
    def test_failed_collection_rejected(self):
        x=sample(2,3);x["status"]="FAILED"
        with self.assertRaises(ValueError):compare(x,sample(2,3,"2026-10-10T00:00:00Z"))
    def test_same_day_is_not_multiday(self):
        result=compare(sample(2,2.4),sample(2.5,2.9,"2026-10-09T00:01:00Z"))
        self.assertEqual(result["status"],"SAME_DAY_OBSERVATIONAL_ONLY")
        self.assertTrue(result["same_utc_day"])
        self.assertFalse(result["multi_day_outcome_verified"])
        self.assertEqual(result["elapsed_seconds"],60)
    def test_nonforward_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            compare(sample(2,2.4),sample(2.5,2.9))
    def test_unmatched_contract(self):
        x=sample(2,3);x["snapshots"][0]["contracts"][0]["occ_symbol"]="OTHER"
        self.assertEqual(compare(x,sample(2,3))["matched_contracts"],0)
