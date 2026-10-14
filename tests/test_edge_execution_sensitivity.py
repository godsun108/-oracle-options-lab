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
        self.assertTrue(all(p["invested_observation_fraction"] is None for p in result["pairs"]))
        self.assertTrue(all(s["mean_excess_vs_zero_yield_cash_pct"] is None for p in result["pairs"] for s in p["scenarios"]))

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

    def test_cash_is_neutral_even_when_costed_market_loses(self):
        a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        ledger=advance(a,report("2026-10-07",[("2026-10-05",100.0),("2026-10-06",100.0),("2026-10-07",100.0)]))
        cash=next(p for p in summarize(ledger)["pairs"] if p["strategy_id"]=="trend_200")
        self.assertEqual(cash["cash_observations"],1)
        self.assertEqual(cash["invested_observation_fraction"],0)
        for s in cash["scenarios"]:
            self.assertEqual(s["mean_excess_vs_zero_yield_cash_pct"],0)
            self.assertEqual(s["mean_excess_vs_cost_free_market_pct"],0)
            self.assertIsNone(s["mean_invested_net_return_pct"])
            self.assertIsNone(s["invested_loss_observations"])
        self.assertGreater(cash["scenarios"][-1]["mean_excess_pct"],0)

    def test_losing_active_samples_remain_losses_and_pending_not_cash(self):
        a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        ledger=advance(a,report("2026-10-07",[("2026-10-05",100.0),("2026-10-06",100.0),("2026-10-07",99.0)]))
        active=next(p for p in summarize(ledger)["pairs"] if p["strategy_id"]=="tsmom_63")
        self.assertEqual(active["outcomes"],1)
        self.assertEqual(active["cash_observations"],0)
        self.assertEqual(active["invested_observation_fraction"],1)
        for s in active["scenarios"]:
            expected=-1-2*s["assumed_total_cost_per_side_bps"]/100
            self.assertAlmostEqual(s["mean_excess_vs_zero_yield_cash_pct"],expected)
            self.assertAlmostEqual(s["mean_invested_net_return_pct"],expected)
            self.assertAlmostEqual(s["worst_invested_observation_pct"],expected)
            self.assertEqual(s["invested_loss_observations"],1)

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
