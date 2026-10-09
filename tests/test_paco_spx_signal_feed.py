import unittest
from datetime import date,timedelta,datetime,timezone
from research.paco_spx_signal_feed import produce

def collection():
    return {"status":"COLLECTED","orders_enabled":False,"collected_at":"2026-10-09T15:00:00+00:00","snapshots":[{"contracts":[{"occ_symbol":"SPY_PUT","type":"put","expiration":"2026-11-20","strike":600,"bid":2,"ask":3}]}]}

class FeedTests(unittest.TestCase):
    def test_no_token(self):
        self.assertEqual(produce("",collection())["status"],"SIGNAL_EVIDENCE_UNAVAILABLE")
    def test_history_does_not_prove_all_time_high(self):
        days=[date(2025,1,1)+timedelta(days=i) for i in range(300)]
        rows=[{"date":d.isoformat(),"close":100+i} for i,d in enumerate(days)]
        result=produce("fake",collection(),fetch=lambda *args:rows,now=datetime(2026,10,9,15,tzinfo=timezone.utc))
        self.assertEqual(result["status"],"HISTORICAL_COVERAGE_UNVERIFIED")
        self.assertEqual(result["candidates"],[])
        self.assertFalse(result["history_coverage_complete_verified"])
    def test_insufficient_bars(self):
        result=produce("fake",collection(),fetch=lambda *args:[{"date":"2026-10-08","close":100}])
        self.assertEqual(result["status"],"INSUFFICIENT_HISTORY")
