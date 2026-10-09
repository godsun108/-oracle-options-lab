import unittest
from research.paco_spx_provenance_gap import assess


class ProvenanceGapTests(unittest.TestCase):
    def test_tradier_prefix_gap(self):
        d = {"symbols": [{"symbol": "SPX", "status": "HISTORY_RETURNED",
                          "first_date": "1994-12-27", "last_date": "2026-10-08", "bars": 7999}]}
        r = assess(d)
        self.assertEqual(r["status"], "HISTORICAL_PREFIX_MISSING")
        self.assertEqual(r["missing_before_tradier_start"]["from"], "1928-01-03")
        self.assertFalse(r["history_coverage_complete_verified"])
        self.assertFalse(r["orders_enabled"])

    def test_missing_history_fails_closed(self):
        r = assess({"symbols": []})
        self.assertEqual(r["status"], "UNVERIFIED_SOURCE_HISTORY")
        self.assertFalse(r["independent_price_series_verified"])

    def test_matching_first_date_does_not_verify_prices(self):
        d = {"symbols": [{"symbol": "SPX", "status": "HISTORY_RETURNED",
                          "first_date": "1928-01-03", "last_date": "2026-10-08", "bars": 10000}]}
        r = assess(d)
        self.assertEqual(r["status"], "DATE_COVERAGE_UNVERIFIED")
        self.assertFalse(r["history_coverage_complete_verified"])


if __name__ == "__main__":
    unittest.main()
