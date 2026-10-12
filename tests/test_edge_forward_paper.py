import copy
import unittest
from research.edge_forward_paper import advance,verify

def report(day,opens):
    return {"schema":"oracle-q-edge-lab-v1","orders_enabled":False,"edge_proven":False,
            "observed_at":day+"T20:00:00+00:00",
            "reports":[{"symbol":"SPY","status":"HISTORICAL_OPEN_PROXY_BACKTEST_ONLY",
                        "price_field":"open_only","last_completed_date":day,
                        "recent_opens":[{"time":d,"open":p} for d,p in opens],
                        "strategies":[{"strategy_id":"tsmom_63","next_session_paper_signal":1},
                                      {"strategy_id":"trend_200","next_session_paper_signal":0}]}]}

class ForwardPaperTests(unittest.TestCase):
    def test_delayed_observation_without_fills(self):
        a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        self.assertEqual(a["signals_registered"],2)
        self.assertEqual(a["outcomes_observed"],0)
        b=advance(a,report("2026-10-06",[("2026-10-05",100.0),("2026-10-06",101.0)]))
        self.assertEqual(b["outcomes_observed"],0)
        c=advance(b,report("2026-10-07",[("2026-10-05",100.0),("2026-10-06",101.0),("2026-10-07",103.0)]))
        self.assertEqual(c["outcomes_observed"],2)
        outcomes=[e for e in c["events"] if e["type"]=="PAPER_OUTCOME_OBSERVED"]
        self.assertAlmostEqual(outcomes[0]["hypothetical_net_return_pct"],100*(103/101-1-.002),5)
        self.assertEqual(outcomes[1]["hypothetical_net_return_pct"],0)
        self.assertFalse(c["fill_verified"])
        self.assertFalse(c["edge_proven"])
        self.assertEqual(len(verify(c)),c["events_recorded"])
    def test_same_day_rerun_does_not_duplicate(self):
        first=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        second=advance(first,report("2026-10-05",[("2026-10-05",100.0)]))
        self.assertEqual(second["events_recorded"],first["events_recorded"])
    def test_chain_tampering_rejected(self):
        first=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        changed=copy.deepcopy(first)
        changed["events"][0]["signal"]=0
        with self.assertRaisesRegex(ValueError,"hash chain"):
            advance(changed,report("2026-10-06",[("2026-10-06",101.0)]))
    def test_price_revision_fails_closed_before_new_settlement(self):
        a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        self.assertEqual(a["open_checkpoints_recorded"],1)
        with self.assertRaisesRegex(ValueError,"SOURCE_OPEN_REVISED"):
            advance(a,report("2026-10-06",[("2026-10-05",100.01),("2026-10-06",101.0)]))
        self.assertEqual(len(verify(a)),a["events_recorded"])
    def test_checkpoints_idempotent_and_hashed(self):
        a=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        b=advance(a,report("2026-10-05",[("2026-10-05",100.0)]))
        self.assertEqual(b["open_checkpoints_recorded"],1)
        self.assertEqual(b["events_recorded"],a["events_recorded"])
        tampered=copy.deepcopy(b)
        tampered["events"][0]["open_price"]=999.0
        with self.assertRaisesRegex(ValueError,"hash chain"):
            verify(tampered)
    def test_after_open_registration_skips_same_day_entry(self):
        a=report("2026-10-05",[("2026-10-05",100.0)])
        a["observed_at"]="2026-10-06T16:00:00+00:00" # Tuesday after 09:30 NY
        first=advance(None,a)
        second=advance(first,report("2026-10-07",[
            ("2026-10-05",100.0),("2026-10-06",101.0),("2026-10-07",102.0)]))
        self.assertEqual(second["outcomes_observed"],0)
        third=advance(second,report("2026-10-08",[
            ("2026-10-05",100.0),("2026-10-06",101.0),
            ("2026-10-07",102.0),("2026-10-08",103.0)]))
        old=[x for x in third["events"] if x["type"]=="PAPER_OUTCOME_OBSERVED" and x["signal_date"]=="2026-10-05"]
        self.assertEqual(len(old),2)
        self.assertTrue(all(x["entry_date"]=="2026-10-07" for x in old))
    def test_legacy_untimestamped_signals_excluded(self):
        from research.edge_forward_paper import digest
        first=advance(None,report("2026-10-05",[("2026-10-05",100.0)]))
        prior=None
        for event in first["events"]:
            event.pop("registered_at",None)
            event["previous_sha256"]=prior
            event["event_sha256"]=digest({k:v for k,v in event.items() if k!="event_sha256"})
            prior=event["event_sha256"]
        first["head_sha256"]=prior
        second=advance(first,report("2026-10-07",[
            ("2026-10-05",100.0),("2026-10-06",101.0),("2026-10-07",102.0)]))
        self.assertEqual(second["signals_excluded_timing"],2)
        self.assertEqual(second["outcomes_observed"],0)
        self.assertEqual(second["pending_signals"],2)
    def test_invalid_report_blocks_signals(self):
        bad=report("2026-10-05",[("2026-10-05",100.0)])
        bad["reports"][0]["status"]="DATA_OR_VALIDATION_FAILURE"
        with self.assertRaises(ValueError):
            advance(None,bad)

if __name__=="__main__":
    unittest.main()
