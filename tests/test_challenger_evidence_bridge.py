import unittest
from unittest.mock import patch
from research.challenger_evidence_bridge import baseline_shadow_score

class EvidenceBridgeTests(unittest.TestCase):
    def test_invalid_ledger_fails_before_scoring(self):
        with self.assertRaises(Exception):
            baseline_shadow_score({"events":[]}, windows=[("2026-10-16","2026-10-19")],
                                  registration_template={})
    def test_duplicate_windows_fail_closed(self):
        with patch("research.challenger_evidence_bridge.audit", return_value={}):
            with self.assertRaises(ValueError):
                baseline_shadow_score({"events":[]},
                    windows=[("2026-10-16","2026-10-19")]*2,
                    registration_template={})
if __name__=="__main__":
    unittest.main()
