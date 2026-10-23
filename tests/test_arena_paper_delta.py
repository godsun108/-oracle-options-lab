import unittest
from research.arena_paper_delta import compare

IDS = [m + "::" + s for m in ("SPY", "QQQ", "IWM", "SMH", "TLT", "GLD")
       for s in ("reversal_5", "trend_200", "tsmom_63")]

def sample(date, equity, sha):
    return {"schema": "oracle-q-arena-agent-positions-v1",
            "source_kind": "REPLAYED_AUDITED_FORWARD_LEDGER",
            "source_generated_at": date, "ledger_head_sha256": sha * 64,
            "orders_enabled": False, "broker_fills_verified": False,
            "price_is_live": False, "edge_proven": False,
            "positions": [{"agent_id": x, "symbol": x.split("::")[0],
                           "equity": equity, "cash": equity, "market_value": 0,
                           "realized_pnl": 0, "unrealized_pnl": 0} for x in IDS]}

class PaperDeltaTests(unittest.TestCase):
    def test_valid_snapshot_comparison(self):
        r = compare(sample("2026-10-20T12:00:00Z", 2000, "a"),
                    sample("2026-10-21T12:00:00Z", 2010, "b"))
        self.assertEqual(r["equity_change"], 180)
        self.assertFalse(r["orders_enabled"])
    def test_rejects_unchanged_lineage(self):
        with self.assertRaises(ValueError):
            compare(sample("2026-10-20T12:00:00Z", 2000, "a"),
                    sample("2026-10-21T12:00:00Z", 2010, "a"))
    def test_rejects_duplicate_agent(self):
        a = sample("2026-10-21T12:00:00Z", 2010, "b")
        a["positions"][-1] = a["positions"][0]
        with self.assertRaises(ValueError):
            compare(sample("2026-10-20T12:00:00Z", 2000, "a"), a)
    def test_rejects_live_flag(self):
        a = sample("2026-10-21T12:00:00Z", 2010, "b")
        a["orders_enabled"] = True
        with self.assertRaises(ValueError):
            compare(sample("2026-10-20T12:00:00Z", 2000, "a"), a)

if __name__ == "__main__":
    unittest.main()
