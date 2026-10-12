import copy
import unittest
from research.edge_forward_paper import advance
from research.edge_forward_scorecard import score,MIN_OUTCOMES_FOR_REVIEW
from tests.test_edge_forward_paper import report

class ForwardScorecardTests(unittest.TestCase):
    def test_empty_forward_signals_never_promoted(self):
        ledger=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        summary=score(ledger,expected_pairs=[("SPY","tsmom_63"),("SPY","trend_200")])
        self.assertEqual(len(summary["pairs"]),2)
        self.assertEqual(summary["outcomes_total"],0)
        self.assertTrue(all(x["status"]=="INSUFFICIENT_FORWARD_SAMPLE" for x in summary["pairs"]))
        self.assertFalse(summary["edge_proven"])

    def test_paired_benchmark_and_cash(self):
        a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        b=advance(a,report("2026-10-06",[("2026-10-05",100.0),("2026-10-06",101.0)]))
        c=advance(b,report("2026-10-07",[("2026-10-05",100.0),("2026-10-06",101.0),("2026-10-07",103.0)]))
        summary=score(c)
        momentum=next(x for x in summary["pairs"] if x["strategy_id"]=="tsmom_63")
        cash=next(x for x in summary["pairs"] if x["strategy_id"]=="trend_200")
        self.assertEqual(momentum["outcomes_observed"],1)
        self.assertEqual(momentum["paired_benchmark_observations"],1)
        self.assertEqual(momentum["mean_excess_vs_buy_hold_pct"],0)
        self.assertEqual(cash["mean_hypothetical_return_pct"],0)
        self.assertLess(cash["mean_excess_vs_buy_hold_pct"],0)
        self.assertFalse(summary["eligible_for_live_trading"])

    def test_hash_tamper_and_benchmark_mismatch_rejected(self):
        a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        b=advance(a,report("2026-10-06",[("2026-10-05",100.0),("2026-10-06",101.0)]))
        c=advance(b,report("2026-10-07",[("2026-10-05",100.0),("2026-10-06",101.0),("2026-10-07",103.0)]))
        changed=copy.deepcopy(c)
        changed["events"][-1]["hypothetical_excess_vs_buy_hold_pct"]=999
        with self.assertRaisesRegex(ValueError,"hash chain"):
            score(changed)
        # Even a correctly rehashed malformed benchmark must be rejected.
        from research.edge_forward_paper import digest
        changed["events"][-1]["event_sha256"]=digest({k:v for k,v in changed["events"][-1].items() if k!="event_sha256"})
        changed["head_sha256"]=changed["events"][-1]["event_sha256"]
        with self.assertRaisesRegex(ValueError,"benchmark excess mismatch"):
            score(changed)

    def test_review_threshold_never_proves_edge(self):
        self.assertEqual(MIN_OUTCOMES_FOR_REVIEW,60)
        a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        with self.assertRaisesRegex(ValueError,"unexpected symbol"):
            score(a,expected_pairs=[("QQQ","tsmom_63")])

if __name__=="__main__":
    unittest.main()
