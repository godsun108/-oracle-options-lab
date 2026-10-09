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
if __name__=="__main__":unittest.main()
