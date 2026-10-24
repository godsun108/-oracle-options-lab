import unittest
from datetime import date,timedelta,datetime,timezone
from research.paco_spx_signal_feed import produce

def collection():
    return {"status":"COLLECTED","orders_enabled":False,"collected_at":"2026-10-09T15:00:00+00:00","snapshots":[{"contracts":[{"occ_symbol":"SPY_PUT","type":"put","expiration":"2026-11-20","strike":600,"bid":2,"ask":3}]}]}

class FeedTests(unittest.TestCase):
    def test_no_token(self):
        self.assertEqual(produce("",collection())["status"],"SIGNAL_EVIDENCE_UNAVAILABLE")
    def test_history_does_not_prove_all_time_high(self):
        days=[date(2025,8,1)+timedelta(days=i) for i in range(434) if (date(2025,8,1)+timedelta(days=i)).weekday()<5]
        rows=[{"date":d.isoformat(),"close":100+i} for i,d in enumerate(days)]
        observed=[]
        def fetch(symbol,*args):
            observed.append(symbol)
            return rows
        result=produce("fake",collection(),fetch=fetch,now=datetime(2026,10,9,15,tzinfo=timezone.utc))
        self.assertEqual(observed,["SPX"])
        self.assertEqual(result["status"],"HISTORICAL_COVERAGE_UNVERIFIED")
        self.assertEqual(result["candidates"],[])
        self.assertFalse(result["history_coverage_complete_verified"])
    def test_insufficient_bars(self):
        result=produce("fake",collection(),fetch=lambda *args:[{"date":"2026-10-08","close":100}])
        self.assertEqual(result["status"],"INSUFFICIENT_HISTORY")


class InvalidHistoryTests(unittest.TestCase):
    NOW=datetime(2026,10,9,15,tzinfo=timezone.utc)

    def rows(self):
        days=[date(2025,8,1)+timedelta(days=i) for i in range(434)]
        return [{"date":d.isoformat(),"close":100+i} for i,d in enumerate(days) if d.weekday()<5]

    def check(self, rows):
        result=produce("fake",collection(),fetch=lambda *args:rows,now=self.NOW)
        self.assertFalse(result["history_coverage_complete_verified"])
        self.assertFalse(result["orders_enabled"])
        self.assertEqual(result["candidates"],[])
        return result

    def test_stale_history_cannot_emit_current_signal(self):
        result=self.check(self.rows()[:-1])
        self.assertEqual(result["status"],"STALE_SPX_HISTORY")
        self.assertFalse(result["spx_record_close"])

    def test_bad_history_not_silently_dropped(self):
        for value in ("NaN",float("inf"),0,-1,True):
            rows=self.rows();rows[20]["close"]=value
            with self.subTest(value=value):
                self.assertEqual(self.check(rows)["status"],"SPX_HISTORY_UNAVAILABLE")

    def test_duplicate_history_not_silently_overwritten(self):
        rows=self.rows()
        self.assertEqual(self.check(rows+[rows[20]])["status"],"SPX_HISTORY_UNAVAILABLE")

    def test_weekend_bar_rejected(self):
        self.assertEqual(self.check(self.rows()+[{"date":"2026-10-03","close":100}])["status"],
                         "SPX_HISTORY_UNAVAILABLE")

    def test_holiday_uses_last_completed_session(self):
        now=datetime(2026,7,3,15,tzinfo=timezone.utc)
        result=produce("fake",collection(),fetch=lambda *args:[],now=now)
        self.assertEqual(result["expected_history_last_date"],"2026-07-02")
