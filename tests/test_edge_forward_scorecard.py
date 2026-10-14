import copy
import unittest
from research.edge_forward_paper import advance
from research.edge_forward_scorecard import score,MIN_OUTCOMES_FOR_REVIEW
from tests.test_edge_forward_paper import report

class ForwardScorecardTests(unittest.TestCase):
    def test_regime_coverage_uses_registration_labels_and_keeps_unknowns(self):
        from tests import test_edge_source_replay as fixtures
        factory=fixtures.PartialMarketTests()
        first=factory.report()
        for market in first['reports']:
            market.pop('regime_context')
        ledger=advance(None,first)
        ledger=advance(ledger,factory.report(13))
        ledger=advance(ledger,factory.report(14))
        before=copy.deepcopy(ledger)
        result=score(ledger)
        self.assertEqual(result['outcomes_total'],18)
        self.assertEqual(result['distinct_outcome_exit_sessions'],1)
        for pair in result['pairs']:
            buckets=pair['regime_coverage']
            self.assertEqual(len(buckets),5)
            unknown=next(b for b in buckets if b['regime']=='UNCLASSIFIED')
            self.assertEqual(unknown['completed_observations'],1)
            self.assertEqual(unknown['pending'],0)
            self.assertEqual(sum(b['pending'] for b in buckets),pair['pending'])
            self.assertEqual(sum(b['completed_observations'] for b in buckets),pair['outcomes_observed'])
            self.assertTrue(all(b['completed_observations']==0 for b in buckets if b['regime']!='UNCLASSIFIED'))
        self.assertEqual(ledger,before)

    def test_legacy_exclusions_are_not_regime_evidence(self):
        from tests.test_edge_forward_integrity_audit import rehash
        ledger=advance(None,report('2026-10-05',[('2026-10-05',100.0)]))
        for event in ledger['events']:
            if event['type']=='SIGNAL_REGISTERED':
                event.pop('registered_at')
                event.pop('source_observed_at')
        rehash(ledger)
        ledger=advance(ledger,report('2026-10-06',[('2026-10-05',100.0),('2026-10-06',101.0)]))
        result=score(ledger)
        self.assertEqual(result['signals_excluded_timing'],2)
        for pair in result['pairs']:
            self.assertEqual(sum(b['valid_signals'] for b in pair['regime_coverage']),1)
            self.assertEqual(sum(b['completed_observations'] for b in pair['regime_coverage']),0)

    def test_invalid_regime_cannot_be_reclassified_as_unknown(self):
        from tests import test_edge_source_replay as fixtures
        from tests.test_edge_forward_integrity_audit import rehash
        ledger=advance(None,fixtures.PartialMarketTests().report())
        next(e for e in ledger['events'] if e['type']=='SIGNAL_REGISTERED')['regime_context']['label']='WRONG'
        rehash(ledger)
        with self.assertRaises(ValueError):score(ledger)

    def test_maturity_uses_holiday_and_early_close_calendar(self):
        source=report("2026-11-24",[("2026-11-24",100.0)])
        source["observed_at"]="2026-11-24T22:00:00Z"
        ledger=advance(None,source)
        pending=score(ledger,as_of="2026-11-27T18:14:59Z")["maturity"]["pending"]
        self.assertEqual(pending[0]["exit_session"],"2026-11-27")
        self.assertEqual(pending[0]["earliest_data_eligibility_utc"],"2026-11-27T18:15:00+00:00")
        self.assertEqual(pending[0]["status"],"WAITING_FOR_DAILY_BAR_ELIGIBILITY")

    def test_pending_maturity_never_creates_outcomes(self):
        ledger=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        for stamp,status in [("2026-10-06T13:29:00Z","WAITING_FOR_ENTRY_SESSION"),
                             ("2026-10-06T13:30:00Z","WAITING_FOR_EXIT_SESSION"),
                             ("2026-10-07T13:30:00Z","WAITING_FOR_DAILY_BAR_ELIGIBILITY"),
                             ("2026-10-07T20:15:00Z","ELIGIBLE_AWAITING_VALIDATED_DATA_OR_SETTLEMENT")]:
            with self.subTest(stamp=stamp):
                result=score(ledger,as_of=stamp)
                self.assertEqual(result["outcomes_total"],0)
                self.assertTrue(all(x["status"]==status for x in result["maturity"]["pending"]))
                self.assertEqual(result["maturity"]["pending"][0]["exit_session"],"2026-10-07")

    def test_maturity_rejects_backdated_or_naive_snapshot(self):
        ledger=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        for stamp in ("2026-10-04T00:00:00Z","2026-10-07"):
            with self.assertRaises(ValueError):score(ledger,as_of=stamp)

    def test_maturity_removes_settled_signals(self):
        a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        b=advance(a,report("2026-10-07",[("2026-10-05",100.0),("2026-10-06",101.0),("2026-10-07",103.0)]))
        result=score(b,as_of="2026-10-07T22:00:00Z")
        self.assertEqual(result["outcomes_total"],2)
        self.assertTrue(all(x["signal_date"]=="2026-10-07" for x in result["maturity"]["pending"]))

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
