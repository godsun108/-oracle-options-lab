import unittest
from research.paco_spx_history_diagnostic import diagnose

class CoverageTests(unittest.TestCase):
    def test_symbol_fallback_and_coverage(self):
        def fetch(symbol,*args):
            if symbol=="$SPX":return []
            return [{"date":"2026-10-08","close":6700}]
        r=diagnose("fake",fetch=fetch)
        self.assertEqual(r["status"],"INSUFFICIENT_HISTORY")
        self.assertEqual(r["symbols"][0]["status"],"NO_BARS")
        self.assertEqual(r["symbols"][1]["bars"],1)
        self.assertFalse(r["signal_verified"])
    def test_missing_token(self):
        self.assertEqual(diagnose("")["status"],"TOKEN_MISSING")
    def test_exception_redacted(self):
        def fetch(*args):raise RuntimeError("sensitive detail")
        r=diagnose("fake",fetch=fetch)
        self.assertEqual(r["symbols"][0]["error_type"],"RuntimeError")
        self.assertNotIn("sensitive detail",str(r))
