import unittest
from evergreen_forward_profit_evidence_v1 import evaluate
def packet(trades=None):
 return {"schema":"oracle.forward-settlements.v1","mode":"RESEARCH_ONLY",
 "ordersEnabled":False,"trades":[] if trades is None else trades}
def trade(i,equity,gross,cost):
 return {"id":str(i),"status":"SETTLED_PAPER","broker_fill_verified":False,
 "gross_pnl":gross,"total_cost":cost,"starting_equity":equity}
class ProfitEvidenceTests(unittest.TestCase):
 def test_empty_evidence_is_not_edge(self):
  r=evaluate(packet())
  self.assertEqual(r["scorecard"]["sample_size"],0)
  self.assertIn("no_settled_paper_trades",r["reasons"])
  self.assertFalse(r["independentlyVerifiedProfitableEdge"])
 def test_net_costs_reduce_profit(self):
  r=evaluate(packet([trade(1,2000,10,12)]),min_trades=1)
  self.assertEqual(r["scorecard"]["net_pnl"],-2)
  self.assertFalse(r["preliminarySelfReportedGatePassed"])
 def test_preliminary_positive_is_not_verified(self):
  trades=[];equity=2000
  for i in range(30):
   trades.append(trade(i,equity,10,1));equity+=9
  r=evaluate(packet(trades))
  self.assertTrue(r["preliminarySelfReportedGatePassed"])
  self.assertFalse(r["independentlyVerifiedProfitableEdge"])
  self.assertFalse(r["paperCandidateEligible"])
 def test_duplicate_trade_refused(self):
  with self.assertRaisesRegex(ValueError,"duplicate"):
   evaluate(packet([trade(1,2000,5,1),trade(1,2004,5,1)]))
 def test_overlapping_equity_refused(self):
  with self.assertRaisesRegex(ValueError,"discontinuity"):
   evaluate(packet([trade(1,2000,5,1),trade(2,2000,5,1)]))
 def test_live_execution_refused(self):
  p=packet();p["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"live execution"):evaluate(p)
if __name__=="__main__":unittest.main()
