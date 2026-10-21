import unittest
from evergreen_net_edge_evidence_v1 import evaluate
def packet(trades):
 return {"schema":"oracle.settled-trades.v1","mode":"RESEARCH_ONLY","ordersEnabled":False,"trades":trades}
def trade(id,gross,fees=0,slippage=0,benchmark=0):
 return dict(id=id,grossPnl=gross,fees=fees,slippageCost=slippage,benchmarkPnl=benchmark)
class NetEdgeTests(unittest.TestCase):
 def test_no_trades_no_edge(self):
  r=evaluate(packet([]));self.assertIsNone(r["netPositive"]);self.assertFalse(r["edgeEstablished"])
 def test_costs_flip_gross_winner(self):
  r=evaluate(packet([trade("a",10,7,5)]))
  self.assertEqual(r["reportedNetPnl"],-2);self.assertEqual(r["reportedWinRate"],0)
 def test_positive_report_not_verified_edge(self):
  r=evaluate(packet([trade("a",100,1,1,20)]))
  self.assertEqual(r["reportedExcessPnl"],78)
  self.assertFalse(r["edgeEstablished"]);self.assertFalse(r["promotionAuthorized"])
 def test_duplicate_trade_refused(self):
  with self.assertRaisesRegex(ValueError,"duplicate"):evaluate(packet([trade("a",1),trade("a",2)]))
 def test_negative_cost_refused(self):
  with self.assertRaisesRegex(ValueError,"negative costs"):evaluate(packet([trade("a",1,-1)]))
 def test_live_mode_refused(self):
  p=packet([]);p["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"live execution"):evaluate(p)
if __name__=="__main__":unittest.main()
