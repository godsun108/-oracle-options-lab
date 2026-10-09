import unittest
from research.options_discount_scanner import screen

def quote(**overrides):
    q={"symbol":"SPY_TEST","bid":1.30,"ask":1.35,"reference_mid":2.40,
       "quote_age_seconds":0.2,"ask_size":10,"dte":45}
    q.update(overrides)
    return q

class ScannerTests(unittest.TestCase):
    def test_discount_is_not_instant_profit(self):
        x=screen([quote()])[0]
        self.assertGreater(x["discount_pct"],40)
        self.assertFalse(x["instant_profit_verified"])
        self.assertLess(x["immediate_roundtrip_net_per_contract"],0)
        self.assertFalse(x["orders_enabled"])
    def test_stale_quote_rejected(self):
        self.assertEqual(screen([quote(quote_age_seconds=20)]),[])
    def test_crossed_or_missing_size_rejected(self):
        self.assertEqual(screen([quote(bid=2.50),quote(ask_size=0)]),[])
    def test_wide_spread_rejected(self):
        self.assertEqual(screen([quote(bid=0.1)]),[])
if __name__=="__main__":
    unittest.main()
