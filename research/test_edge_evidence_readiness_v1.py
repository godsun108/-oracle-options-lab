import unittest
from edge_evidence_readiness_v1 import evaluate

def envelope(**kw):
    return {"schema":"oracle-q-edge-evidence-input-v1","mode":"RESEARCH_ONLY",
            "orders_enabled":False,"observations":[],"settled_paper_trades":[],**kw}

class ReadinessTests(unittest.TestCase):
    def test_no_trades_is_no_verified_edge(self):
        result=evaluate(envelope())
        self.assertEqual(result["status"],"NO_SETTLED_PAPER_TRADES")
        self.assertIsNone(result["metrics"])
        self.assertFalse(result["verified_edge"])
    def test_observations_cannot_become_trades(self):
        p=envelope()
        p["observations"]=[{"broker_fills_verified":False,"realized_pnl_available":False}]
        r=evaluate(p)
        self.assertEqual(r["observation_count"],1)
        self.assertEqual(r["settled_paper_trade_count"],0)
    def test_rejects_realized_observation_claim(self):
        p=envelope()
        p["observations"]=[{"broker_fills_verified":False,"realized_pnl_available":True}]
        with self.assertRaisesRegex(ValueError,"observation falsely"):evaluate(p)
    def test_rejects_enabled_orders(self):
        p=envelope();p["orders_enabled"]=True
        with self.assertRaisesRegex(ValueError,"unsafe"):evaluate(p)
    def test_settled_trade_metrics_not_provenance(self):
        p=envelope()
        p["settled_paper_trades"]=[{"id":"synthetic-1","status":"SETTLED_PAPER",
            "broker_fill_verified":False,"gross_pnl":3.,"total_cost":1.,
            "starting_equity":2000.}]
        r=evaluate(p)
        self.assertEqual(r["metrics"]["net_pnl"],2.)
        self.assertFalse(r["verified_edge"])
        self.assertFalse(r["promotion_authorized"])

if __name__=="__main__":unittest.main()
