import copy
import unittest
from datetime import datetime, timezone, timedelta
from research.arena_public_progress import project

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
MARKETS = ("SPY", "QQQ", "IWM", "SMH", "TLT", "GLD")


def review():
    return {"schema": "oracle-q-arena-frozen-league-v1",
            "source_kind": "AUDITED_FROZEN_PAPER_LEAGUE",
            "season_id": "etf-open-paper-2026-10-v1",
            "as_of": (NOW-timedelta(hours=1)).isoformat(),
            "ledger_head_sha256": "a"*64, "rules_sha256": "b"*64,
            "live": False, "orders_enabled": False, "edge_proven": False,
            "rows": [{"candidate_id": m+"::frozen-three-strategy-basket",
                      "market": m, "status": "ACCUMULATING_FORWARD_EVIDENCE",
                      "completed_common_sessions": 0, "required_sessions": 60,
                      "missing_eligible_windows": [], "net_return_pct": None,
                      "max_drawdown_pct": None, "edge_proven": False,
                      "eligible_for_live_trading": False} for m in MARKETS]}


class PublicProjectionTests(unittest.TestCase):
    def test_zero_progress_is_explicit_and_nonlive(self):
        feed = project(review(), now=NOW)
        self.assertEqual(len(feed["rows"]), 6)
        self.assertEqual(feed["rows"][0]["completed_common_sessions"], 0)
        self.assertIsNone(feed["rows"][0]["net_return_pct"])
        self.assertFalse(feed["live"])

    def test_rejects_partial_return(self):
        data = review()
        data["rows"][0]["net_return_pct"] = 1.0
        with self.assertRaises(ValueError):
            project(data, now=NOW)

    def test_rejects_fabricated_completion(self):
        data = review()
        data["rows"][0]["status"] = "FIXED_WINDOW_DESCRIPTIVE_RESULT"
        with self.assertRaises(ValueError):
            project(data, now=NOW)

    def test_rejects_duplicate_market(self):
        data = review()
        data["rows"][1] = copy.deepcopy(data["rows"][0])
        with self.assertRaises(ValueError):
            project(data, now=NOW)

    def test_rejects_stale_snapshot(self):
        with self.assertRaises(ValueError):
            project(review(), now=NOW+timedelta(days=6))

    def test_rejects_live_claim(self):
        data = review()
        data["orders_enabled"] = True
        with self.assertRaises(ValueError):
            project(data, now=NOW)

    def test_completed_season_must_be_complete_and_finite(self):
        data = review()
        for row in data["rows"]:
            row.update(status="FIXED_WINDOW_DESCRIPTIVE_RESULT",
                       completed_common_sessions=60, net_return_pct=4.0,
                       max_drawdown_pct=-2.0)
        feed = project(data, now=NOW)
        self.assertEqual(feed["rows"][0]["net_return_pct"], 4.0)


if __name__ == "__main__":
    unittest.main()
