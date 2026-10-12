import copy
import unittest

from research.edge_forward_paper import advance, digest
from research.edge_forward_integrity_audit import audit
from tests.test_edge_forward_paper import report

def sequence():
    a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
    b=advance(a,report("2026-10-06",[("2026-10-05",100.0),("2026-10-06",101.0)]))
    return advance(b,report("2026-10-07",[("2026-10-05",100.0),("2026-10-06",101.0),("2026-10-07",103.0)]))

def rehash(ledger):
    previous=None
    for event in ledger["events"]:
        event["previous_sha256"]=previous
        event["event_sha256"]=digest({k:v for k,v in event.items() if k!="event_sha256"})
        previous=event["event_sha256"]
    ledger["head_sha256"]=previous

class IntegrityAuditTests(unittest.TestCase):
    def test_settled_prices_and_timing_audit(self):
        result=audit(sequence())
        self.assertEqual(result["forward_outcomes"],2)
        self.assertEqual(result["registered_signals"],6)
        self.assertTrue(result["chronological_entry_validation"])
        self.assertFalse(result["edge_proven"])

    def test_rehashed_false_profit_rejected(self):
        ledger=sequence()
        for event in ledger["events"]:
            if event["type"]=="PAPER_OUTCOME_OBSERVED":
                event["hypothetical_net_return_pct"]=500.0
                break
        rehash(ledger)
        with self.assertRaisesRegex(ValueError,"arithmetic mismatch"):
            audit(ledger)

    def test_rehashed_hindsight_entry_rejected(self):
        ledger=sequence()
        for event in ledger["events"]:
            if event["type"]=="SIGNAL_REGISTERED" and event["signal_date"]=="2026-10-05":
                event["registered_at"]="2026-10-07T20:00:00+00:00"
        rehash(ledger)
        with self.assertRaisesRegex(ValueError,"retroactive opening price"):
            audit(ledger)

    def test_rehashed_checkpoint_price_rejected(self):
        ledger=sequence()
        for event in ledger["events"]:
            if event["type"]=="SOURCE_OPEN_CHECKPOINT" and event["open_date"]=="2026-10-06":
                event["open_price"]=90.0
        rehash(ledger)
        with self.assertRaisesRegex(ValueError,"arithmetic mismatch"):
            audit(ledger)

    def test_unquarantined_legacy_signal_rejected(self):
        ledger=sequence()
        for event in ledger["events"]:
            if event["type"]=="SIGNAL_REGISTERED":
                event.pop("registered_at",None)
        rehash(ledger)
        with self.assertRaisesRegex(ValueError,"legacy untimed signal"):
            audit(ledger)

if __name__=="__main__":
    unittest.main()
