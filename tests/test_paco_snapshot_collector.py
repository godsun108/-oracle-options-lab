import unittest
from datetime import date
from research.paco_snapshot_collector import collect

def chain(exp):
    return {"provider":"tradier","orders_enabled":False,"expiration":exp,
            "contracts":[{"occ_symbol":"SPY_TEST","bid":1,"ask":2,
                          "provider_timestamp":None,"quote_freshness_verified":False}]}
class CollectorTests(unittest.TestCase):
    def test_30_to_60_dte_and_no_execution_claims(self):
        r=collect("fixture",today=date(2026,10,9),
                  fetch_expirations=lambda:["2026-10-10","2026-11-13","2026-12-04"],
                  fetch_options=chain)
        self.assertEqual(r["expirations_requested"],["2026-11-13","2026-12-04"])
        self.assertFalse(r["provider_quote_freshness_verified"])
        self.assertFalse(r["orders_enabled"])
        self.assertEqual(len(r["sha256"]),64)
    def test_empty_expirations_fail_closed(self):
        with self.assertRaises(ValueError):
            collect("fixture",today=date(2026,10,9),
                    fetch_expirations=lambda:[],fetch_options=chain)
    def test_no_token_fail_closed(self):
        with self.assertRaises(ValueError):
            collect("",fetch_expirations=lambda:[],fetch_options=chain)
if __name__=="__main__":unittest.main()
