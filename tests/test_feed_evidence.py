import datetime as dt
import unittest
from research.feed_evidence import assess
from research.multi_market_observer import SYMBOLS

NOW=dt.datetime(2026,10,9,0,0,tzinfo=dt.timezone.utc)
def fixture():
    return {"schema":"oracle-q-multi-market-observation-v1",
            "provider":"tradier","orders_enabled":False,"research_only":True,
            "results":[{"symbol":s,"status":"OBSERVATION_ONLY","as_of":"2026-10-08","bars":220} for s in SYMBOLS]}
class FeedEvidenceTests(unittest.TestCase):
    def test_good_observations(self):
        self.assertEqual(assess(fixture(),NOW)["status"],"PASS")
    def test_missing_symbols(self):
        p=fixture()
        p["results"].pop()
        self.assertEqual(assess(p,NOW)["status"],"FAIL")
    def test_reject_errors_and_unsafe(self):
        p=fixture()
        p["orders_enabled"]=True
        p["results"][0]["status"]="DATA_ERROR"
        self.assertEqual(assess(p,NOW)["status"],"FAIL")
    def test_reject_stale(self):
        p=fixture()
        p["results"][0]["as_of"]="2026-09-01"
        self.assertEqual(assess(p,NOW)["status"],"FAIL")
if __name__=="__main__":
    unittest.main()
