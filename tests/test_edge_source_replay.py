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


if __name__=="__main__":unittest.main()
