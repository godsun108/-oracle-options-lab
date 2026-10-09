import unittest
from research.paco_quote_evidence import validate

NOW="2026-10-09T09:30:01-04:00"
def q(**kw):
    x={"occ_symbol":"SPY261113P00600000","provider":"Tradier","provider_quote_id":"fixture-1",
       "provider_timestamp":"2026-10-09T09:30:00-04:00","bid":1.30,"ask":1.35,
       "bid_size":10,"ask_size":10}
    x.update(kw);return x
class QuoteEvidenceTests(unittest.TestCase):
    def test_accepts_structurally_valid_declared_quote(self):
        r=validate([q()],now_iso=NOW)
        self.assertEqual(len(r["quotes"]),1)
        self.assertFalse(r["independently_authenticated"])
        self.assertFalse(r["broker_orders_enabled"])
    def test_stale_and_future_rejected(self):
        r=validate([q(provider_timestamp="2026-10-09T09:29:00-04:00"),
                    q(provider_timestamp="2026-10-09T09:30:02-04:00")],now_iso=NOW)
        self.assertEqual(len(r["quotes"]),0)
        self.assertEqual(len(r["rejected"]),2)
    def test_crossed_rejected(self):
        r=validate([q(bid=1.5)],now_iso=NOW)
        self.assertEqual(len(r["rejected"]),1)
    def test_missing_provenance_rejected(self):
        r=validate([q(provider_quote_id="")],now_iso=NOW)
        self.assertEqual(len(r["quotes"]),0)
    def test_duplicate_rejected(self):
        r=validate([q(),q()],now_iso=NOW)
        self.assertEqual(len(r["quotes"]),1)
        self.assertEqual(len(r["rejected"]),1)
if __name__=="__main__":unittest.main()
