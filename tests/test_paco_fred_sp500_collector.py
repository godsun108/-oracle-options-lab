import unittest
from research.paco_fred_sp500_collector import parse_csv, collect


class FakeResponse:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return self.body[:limit]


class FredCollectorTests(unittest.TestCase):
    def test_parse_fred_csv(self):
        rows = parse_csv("observation_date,SP500\n2026-10-07,7000.50\n2026-10-08,.\n2026-10-09,7002.00\n")
        self.assertEqual(len(rows), 2)

    def test_reject_other_series(self):
        with self.assertRaises(ValueError):
            parse_csv("DATE,DGS10\n2026-10-07,4.2\n")

    def test_collect_provenance(self):
        r = collect(opener=lambda req, timeout: FakeResponse(b"observation_date,SP500\n2026-10-07,7000\n"))
        self.assertEqual(r["observation_count"], 1)
        self.assertEqual(len(r["sha256"]), 64)
        self.assertFalse(r["history_coverage_complete_verified"])
        self.assertFalse(r["orders_enabled"])


if __name__ == "__main__":
    unittest.main()
