import copy
import unittest

from research.edge_execution_sensitivity import summarize
from research.edge_forward_integrity_audit import audit
from research.edge_forward_paper import advance
from tests.test_edge_forward_paper import report
from tests.test_edge_forward_integrity_audit import sequence, rehash


class ExecutionTests(unittest.TestCase):
    def test_no_results_are_not_zero_returns(self):
        ledger = advance(None, report("2026-10-05", [("2026-10-05", 100.0)]))
        result = summarize(ledger)
        self.assertTrue(all(p["status"] == "NO_FORWARD_OUTCOMES" for p in result["pairs"]))
        self.assertTrue(all(s["mean_net_return_pct"] is None for p in result["pairs"] for s in p["scenarios"]))

    def test_cost_stress_matches_ledger_and_preserves_it(self):
        ledger = sequence()
        before = copy.deepcopy(ledger)
        result = summarize(ledger)
        long = next(p for p in result["pairs"] if p["strategy_id"] == "tsmom_63")
        returns = [s["mean_net_return_pct"] for s in long["scenarios"]]
        self.assertEqual(returns, sorted(returns, reverse=True))
        outcome = next(e for e in ledger["events"] if e["type"] == "PAPER_OUTCOME_OBSERVED" and e["strategy_id"] == "tsmom_63")
        self.assertEqual(returns[1], outcome["hypothetical_net_return_pct"])
        self.assertAlmostEqual(returns[0] - returns[-1], 1.0, places=6)
        cash = next(p for p in result["pairs"] if p["strategy_id"] == "trend_200")
        self.assertTrue(all(s["mean_net_return_pct"] == 0 for s in cash["scenarios"]))
        self.assertFalse(result["eligible_for_live_trading"])
        self.assertEqual(ledger, before)

    def test_rehashed_false_arithmetic_cannot_enter_cost_report(self):
        ledger = sequence()
        next(e for e in ledger["events"] if e["type"] == "PAPER_OUTCOME_OBSERVED")["hypothetical_net_return_pct"] = 99
        rehash(ledger)
        with self.assertRaisesRegex(ValueError, "arithmetic mismatch"):
            summarize(ledger)

    def test_rehashed_impossible_source_times_rejected(self):
        for kind in ("SIGNAL_REGISTERED", "SOURCE_OPEN_CHECKPOINT", "PAPER_OUTCOME_OBSERVED"):
            ledger = sequence()
            event = next(e for e in ledger["events"] if e["type"] == kind)
            event["source_observed_at"] = "2026-10-01T21:00:00+00:00"
            rehash(ledger)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "source timestamp"):
                audit(ledger)

    def test_source_cannot_arrive_after_registration(self):
        ledger = sequence()
        event = next(e for e in ledger["events"] if e["type"] == "SIGNAL_REGISTERED")
        event["source_observed_at"] = "2026-10-05T22:00:00+00:00"
        rehash(ledger)
        with self.assertRaisesRegex(ValueError, "source timestamp"):
            audit(ledger)


if __name__ == "__main__":
    unittest.main()
