import unittest
from research.paco_spx_fred_crosscheck import compare


class FredCrosscheckTests(unittest.TestCase):
    def test_matching_dates(self):
        t = [{"date":"2026-10-07","close":7000.0},{"date":"2026-10-08","close":7001.0}]
        f = [{"date":"2026-10-07","value":"7000.00"},{"date":"2026-10-08","value":"7001.01"}]
        r = compare(t,f)
        self.assertEqual(r["status"],"OVERLAP_MATCHED")
        self.assertEqual(r["compared_dates"],2)
        self.assertFalse(r["history_coverage_complete_verified"])
        self.assertFalse(r["orders_enabled"])

    def test_mismatch_and_missing(self):
        t = [{"date":"2026-10-07","close":7000.0}]
        f = [{"date":"2026-10-07","value":"7005"},{"date":"2026-10-08","value":"."}]
        r = compare(t,f)
        self.assertEqual(r["status"],"MISMATCHES_FOUND")
        self.assertEqual(r["mismatch_count"],1)
        self.assertEqual(r["fred_valid_dates"],1)

    def test_no_overlap_fails_closed(self):
        r = compare([{"date":"2026-10-07","close":7000}],
                    [{"date":"2026-10-08","value":"7000"}])
        self.assertEqual(r["status"],"NO_OVERLAP")
        self.assertFalse(r["history_coverage_complete_verified"])

    def test_bad_tolerance(self):
        with self.assertRaises(ValueError):
            compare([],[],tolerance=-1)


if __name__ == "__main__":
    unittest.main()
