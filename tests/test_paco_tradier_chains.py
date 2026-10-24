import io
import json
import unittest
from research.paco_tradier_chains import fetch_chain

class Response(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
def fake(req,timeout):
    assert req.full_url.startswith("https://api.tradier.com/v1/markets/options/chains?")
    assert req.get_method()=="GET"
    return Response(json.dumps({"options":{"option":[{
        "symbol":"SPY261113P00600000","option_type":"put",
        "bid":1.30,"ask":1.35,"bidsize":4,"asksize":5,"strike":600
    }]}}).encode())
class ChainTests(unittest.TestCase):
    def test_readonly_snapshot_does_not_fake_freshness(self):
        r=fetch_chain("SPY","2026-11-13","fixture-token",opener=fake,
                      observed_at="2026-10-09T14:00:00+00:00")
        self.assertEqual(len(r["contracts"]),1)
        self.assertIsNone(r["contracts"][0]["provider_timestamp"])
        self.assertFalse(r["quote_freshness_verified"])
        self.assertFalse(r["orders_enabled"])
    def test_requires_token(self):
        with self.assertRaises(ValueError):
            fetch_chain("SPY","2026-11-13","",opener=fake)
    def test_rejects_other_underlying(self):
        with self.assertRaises(ValueError):
            fetch_chain("QQQ","2026-11-13","fixture-token",opener=fake)

class NonfiniteChainTests(unittest.TestCase):
    def test_nonfinite_quotes_never_enter_snapshots(self):
        for price in (float('nan'),float('inf'),-float('inf')):
            def opener(req,timeout):
                return Response(json.dumps({'options':{'option':{
                    'symbol':'SPY261113P00600000','option_type':'put',
                    'bid':price,'ask':2,'bidsize':1,'asksize':1}}}).encode())
            with self.subTest(price=price):
                r=fetch_chain('SPY','2026-11-13','fixture',opener=opener)
                self.assertEqual(r['contracts'],[])


class ProviderTimingTests(unittest.TestCase):
    NOW="2026-10-09T14:00:00+00:00"

    def timing(self,bid,ask):
        from research.paco_tradier_chains import timing_evidence
        return timing_evidence({"bid_date":bid,"ask_date":ask},self.NOW)

    def epoch(self):
        from datetime import datetime
        return int(datetime.fromisoformat(self.NOW).timestamp())

    def test_both_sides_must_be_recent(self):
        t=self.epoch()
        r=self.timing(t-1,t-2)
        self.assertTrue(r["both_sides_within_2_seconds"])
        self.assertFalse(r["independent_quote_freshness_verified"])
        r=self.timing(t-1,t-3)
        self.assertFalse(r["both_sides_within_2_seconds"])
        self.assertEqual(r["ask"]["status"],"STALE")

    def test_future_missing_and_wrong_units_fail_closed(self):
        t=self.epoch()
        for bad in (t+1,None,True,"123",t*1000000,0):
            with self.subTest(value=bad):
                self.assertFalse(self.timing(t,bad)["both_sides_within_2_seconds"])

    def test_timestamp_retained_in_collected_contract(self):
        t=self.epoch()
        def opener(req,timeout):
            return Response(json.dumps({"options":{"option":{
                "symbol":"SPY261113P00600000","option_type":"put",
                "bid":1,"ask":2,"bidsize":3,"asksize":4,
                "bid_date":t-1,"ask_date":t}}}).encode())
        r=fetch_chain("SPY","2026-11-13","fixture",opener=opener,observed_at=self.NOW)
        self.assertEqual(r["provider_timestamp_contracts"],1)
        self.assertEqual(r["provider_recent_contracts"],1)
        c=r["contracts"][0]
        self.assertEqual(c["provider_quote_timing"]["bid"]["raw_unix_timestamp"],t-1)
        self.assertFalse(c["executable_fill_verified"])
        self.assertFalse(r["quote_freshness_verified"])
        self.assertIsNone(c["provider_quote_id"])

    def test_millisecond_timestamps_retain_precision_and_units(self):
        t=self.epoch()
        r=self.timing(t*1000-500,t*1000-1500)
        self.assertTrue(r["both_sides_within_2_seconds"])
        self.assertEqual(r["bid"]["age_seconds"],0.5)
        self.assertEqual(r["ask"]["age_seconds"],1.5)
        self.assertEqual(r["bid"]["unit"],"milliseconds")

    def test_actual_production_timestamp_is_stale(self):
        from research.paco_tradier_chains import timing_evidence
        r=timing_evidence({"bid_date":1792786499000,"ask_date":1792786499000},
                          "2026-10-24T22:36:06.747819+00:00")
        self.assertEqual(r["bid"]["status"],"STALE")
        self.assertEqual(r["bid"]["timestamp"],"2026-10-23T20:14:59+00:00")
        self.assertFalse(r["both_sides_within_2_seconds"])

    def test_naive_observation_clock_rejected(self):
        from research.paco_tradier_chains import timing_evidence
        with self.assertRaises(ValueError):timing_evidence({},"2026-10-09T14:00:00")

if __name__=="__main__":unittest.main()
