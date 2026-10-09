import unittest
from research.paco_quote_outcome_audit import evaluate

def sample(a=2.4,b=2.5):
    return {"schema":"paco-premium-comparison-v1","status":"COMPARABLE","orders_enabled":False,"matched_contracts":1,"contracts":[{"occ_symbol":"SPY_TEST","earlier_ask":a,"later_bid":b}]}

class AuditTests(unittest.TestCase):
    def test_fees_and_no_fills(self):
        r=evaluate(sample())
        self.assertEqual(r["audited_contracts"],1)
        self.assertAlmostEqual(r["hypothetical_outcomes"][0]["hypothetical_net_usd"],8.7)
        self.assertFalse(r["strategy_profitability_proven"])
        self.assertFalse(r["trade_fills_verified"])
    def test_negative_spread(self):
        r=evaluate(sample(2.5,2.4))
        self.assertEqual(r["positive_quote_outcomes"],0)
    def test_bad_provenance(self):
        s=sample();s["orders_enabled"]=True
        with self.assertRaises(ValueError):evaluate(s)
    def test_bad_fees(self):
        with self.assertRaises(ValueError):evaluate(sample(),fee_per_side=-1)
    def test_missing_quotes(self):
        r=evaluate(sample(0,2))
        self.assertEqual(r["skipped_contracts"],1)
        self.assertEqual(r["status"],"INSUFFICIENT_DATA")
