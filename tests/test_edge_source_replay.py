import copy
import unittest
from research.edge_lab import run
from research.edge_source_replay import audit
from research.edge_forward_paper import digest
from tests.test_edge_lab import REGISTRY, NOW, bars


class SourceReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=run(REGISTRY,"synthetic-token",fetch=lambda *args:bars(330),now=NOW)

    def test_rejected_rows_are_retained_without_becoming_valid_evidence(self):
        for bad in (0.0,float("nan")):
            raw=bars(330);raw[12]["open"]=bad
            report=run(REGISTRY,"synthetic-token",fetch=lambda *args:raw,now=NOW)
            market=report["reports"][0]
            self.assertEqual(market["status"],"DATA_OR_VALIDATION_FAILURE")
            if bad==0:
                self.assertEqual(market["source_evidence"]["rows"][12]["open"],0)
            else:
                self.assertIn("NaN",market["rejected_parsed_payload_text"])
                self.assertNotIn("source_evidence",market)
            with self.assertRaises(ValueError):audit(report,REGISTRY)

    def test_all_signals_reproduced_without_publication_claim(self):
        result=audit(self.report,REGISTRY)
        self.assertEqual(len(result["markets"]),6)
        self.assertEqual(sum(m["strategies_replayed"] for m in result["markets"]),18)
        self.assertFalse(result["publication_time_verified"])
        self.assertFalse(result["eligible_for_live_trading"])
        self.assertNotIn("synthetic-token",str(self.report))

    def test_mutated_source_signal_receipt_or_publication_fails(self):
        for case in ("rows","rehash","signal","receipt","publication","missing","duplicate"):
            changed=copy.deepcopy(self.report)
            m=changed["reports"][0]
            if case=="rows":m["source_evidence"]["rows"][0]["open"]+=1
            elif case=="rehash":
                m["source_evidence"]["rows"][-1]["open"]+=1
                m["source_payload_sha256"]=digest(m["source_evidence"]["rows"])
            elif case=="signal":m["strategies"][0]["next_session_paper_signal"]^=1
            elif case=="receipt":m["source_evidence"]["received_at"]="2099-01-01T00:00:00Z"
            elif case=="publication":m["source_evidence"]["publication_time_verified"]=True
            elif case=="missing":del m["source_evidence"]
            else:changed["reports"].append(copy.deepcopy(m))
            with self.subTest(case=case),self.assertRaises(ValueError):audit(changed,REGISTRY)


class PartialMarketTests(unittest.TestCase):
    def report(self, day=12, blocked=()):
        from unittest.mock import patch
        from datetime import datetime, timezone
        stamp=datetime(2026,10,day,22,tzinfo=timezone.utc)
        raw=bars(200)
        for extra in range(13,day+1):
            raw.append(dict(raw[-1],date=f"2026-10-{extra}",open=raw[-1]["open"]+.15))
        raw=raw[-200:]
        def fetch(symbol,*args):
            result=copy.deepcopy(raw)
            if symbol in blocked:result[10]["open"]="NaN"
            return result
        with patch("research.edge_lab.datetime") as clock:
            clock.now.return_value=stamp
            return run(REGISTRY,"synthetic-token",fetch=fetch,now=stamp,mode="forward")

    def test_blocked_markets_preserve_pending_and_full_statistical_family(self):
        from research.edge_forward_paper import advance
        from research.edge_forward_scorecard import score_report
        first=self.report()
        prior=advance(None,first)
        partial=self.report(blocked=("IWM","GLD"))
        with self.assertRaises(ValueError):audit(partial,REGISTRY)
        with self.assertRaises(ValueError):advance(prior,partial)
        replay=audit(partial,REGISTRY,allow_partial=True)
        self.assertEqual(len(replay["markets"]),4)
        self.assertEqual(set(replay["blocked_markets"]),{"IWM","GLD"})
        after=advance(prior,partial,allow_partial=True)
        self.assertEqual(after["events"],prior["events"])
        self.assertEqual(after["head_sha256"],prior["head_sha256"])
        for day in (13,14):
            partial=self.report(day,blocked=("IWM","GLD"))
            audit(partial,REGISTRY,allow_partial=True)
            after=advance(after,partial,allow_partial=True)
        added=after["events"][len(prior["events"]):]
        self.assertTrue(added)
        self.assertFalse(any(e["symbol"] in ("IWM","GLD") for e in added))
        self.assertEqual(after["events"][:len(prior["events"])],prior["events"])
        score=score_report(after,partial,as_of=partial["observed_at"],allow_partial=True)
        self.assertEqual(score["collection_health"],"PARTIAL_MARKET_DATA")
        self.assertEqual(len(score["pairs"]),18)
        self.assertEqual(score["outcomes_total"],12)
        for pair in score["pairs"]:
            self.assertEqual(pair["exploratory_uncertainty"]["hypothesis_family_size"],18)
            if pair["symbol"] in ("IWM","GLD"):
                self.assertEqual(pair["current_market_data_status"],"BLOCKED")
                self.assertEqual(pair["pending"],1)
                self.assertEqual(pair["outcomes_observed"],0)
                self.assertIsNone(pair["mean_hypothetical_return_pct"])
        self.assertFalse(score["edge_proven"])
        self.assertFalse(score["eligible_for_live_trading"])

    def test_partial_cannot_hide_missing_markets_or_unknown_states(self):
        from research.edge_forward_paper import advance
        from research.edge_forward_scorecard import score_report
        valid=self.report()
        for case in ("missing","duplicate","all_blocked","unknown","historical"):
            report=copy.deepcopy(valid)
            if case=="missing":report["reports"].pop()
            elif case=="duplicate":report["reports"].append(report["reports"][0])
            elif case=="all_blocked":
                for m in report["reports"]:m["status"]="DATA_OR_VALIDATION_FAILURE"
            else:
                report["reports"][0]["status"]="DATA_OR_VALIDATION_FAILURE" if case=="historical" else "UNKNOWN"
                if case=="historical":report["collection_mode"]="historical"
            with self.subTest(case=case):
                for operation in (lambda:audit(report,REGISTRY,allow_partial=True),
                                  lambda:advance(None,report,allow_partial=True),
                                  lambda:score_report(None,report,as_of=NOW.isoformat(),allow_partial=True)):
                    with self.assertRaises(ValueError):operation()

    def test_partial_does_not_mask_valid_market_tampering_or_missing_strategy(self):
        from research.edge_forward_paper import advance
        from research.edge_forward_scorecard import score_report
        report=self.report(blocked=("IWM","GLD"))
        report["reports"][0]["source_evidence"]["rows"][0]["open"]+=1
        with self.assertRaises(ValueError):audit(report,REGISTRY,allow_partial=True)
        report=self.report(blocked=("IWM","GLD"))
        report["reports"][0]["strategies"].pop()
        with self.assertRaises(ValueError):score_report(None,report,as_of=NOW.isoformat(),allow_partial=True)
        prior=advance(None,self.report())
        report=self.report(blocked=("IWM","GLD"))
        report["reports"][0]["recent_opens"][0]["open"]+=1
        with self.assertRaises(ValueError):advance(prior,report,allow_partial=True)


if __name__=="__main__":unittest.main()
