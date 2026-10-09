import unittest
from research.options_discount_scanner import screen

def quote(**overrides):
    q={"symbol":"SPY_TEST","type":"put","bid":1.30,"ask":1.35,"reference_mid":2.40,
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
    def test_high_prioritizes_puts_and_low_prioritizes_calls(self):
        puts=quote(symbol="SPY_P",type="put",dte=45)
        calls=quote(symbol="SPY_C",type="call",dte=35)
        high=screen([calls,puts],market_regime="HIGH")
        low=screen([puts,calls],market_regime="LOW")
        self.assertEqual([x["type"] for x in high],["put","call"])
        self.assertEqual([x["type"] for x in low],["call","put"])
        self.assertTrue(high[0]["directional_priority"])
        self.assertTrue(low[0]["directional_priority"])
    def test_expiration_guards(self):
        self.assertEqual(screen([quote(type="put",dte=70),quote(type="call",dte=29)]),[])
    def test_unknown_regime_rejected(self):
        with self.assertRaises(ValueError):
            screen([],market_regime="UNKNOWN")
    def test_stale_quote_rejected(self):
        self.assertEqual(screen([quote(quote_age_seconds=20)]),[])
    def test_crossed_or_missing_size_rejected(self):
        self.assertEqual(screen([quote(bid=2.50),quote(ask_size=0)]),[])
    def test_wide_spread_rejected(self):
        self.assertEqual(screen([quote(bid=0.1)]),[])
if __name__=="__main__":
    unittest.main()
