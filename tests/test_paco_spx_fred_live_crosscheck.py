import unittest
from datetime import date
from research.paco_spx_fred_live_crosscheck import produce


class LiveCrosscheckTests(unittest.TestCase):
    def test_matches_and_remains_unverified(self):
        fred = {"sha256": "test-sha", "observations": [{"date":"2026-10-08","value":7000.0}]}
        calls = []
        def fetch(symbol, token, start, end):
            calls.append((symbol, token, start, end))
            return [{"date":"2026-10-08","close":7000.0}]
        r = produce(fred, "read-only-token", fetch=fetch, today=date(2026,10,9))
        self.assertEqual(r["status"], "OVERLAP_MATCHED")
        self.assertEqual(calls[0][0], "SPX")
        self.assertEqual(r["fred_sha256"], "test-sha")
        self.assertFalse(r["history_coverage_complete_verified"])
        self.assertFalse(r["orders_enabled"])

    def test_missing_token(self):
        r = produce({"observations":[{"date":"2026-10-08","value":7000}]}, None)
        self.assertEqual(r["status"], "SOURCE_UNAVAILABLE")

    def test_bad_fetch_fails_closed(self):
        def bad(*args):
            raise ValueError("unavailable")
        r = produce({"observations":[{"date":"2026-10-08","value":7000}]}, "token", fetch=bad)
        self.assertEqual(r["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(r["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
