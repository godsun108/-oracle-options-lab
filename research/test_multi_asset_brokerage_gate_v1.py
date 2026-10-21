import unittest
from multi_asset_brokerage_gate_v1 import assess
def intent(market="FX"):
 return {"market":market,"asOf":"2026-10-21T15:00:00Z","mode":"RESEARCH_ONLY",
 "ordersEnabled":False,"verifiedVenueSession":True,"verifiedQuote":True,"riskApproved":True}
class BrokerageGateTests(unittest.TestCase):
 def test_all_asset_classes_paper_only(self):
  for m in ("FX","CRYPTO","US_EQUITY","US_OPTIONS","FUTURES"):
   r=assess(intent(m))
   self.assertTrue(r["paperCandidateEligible"])
   self.assertFalse(r["liveOrderAuthorized"])
 def test_unverified_session_blocks_paper(self):
  p=intent();p["verifiedVenueSession"]=False
  self.assertFalse(assess(p)["paperCandidateEligible"])
 def test_missing_quote_blocks_paper(self):
  p=intent();p["verifiedQuote"]=False
  self.assertFalse(assess(p)["paperCandidateEligible"])
 def test_risk_blocks_paper(self):
  p=intent();p["riskApproved"]=False
  self.assertFalse(assess(p)["paperCandidateEligible"])
 def test_live_orders_refused(self):
  p=intent();p["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"live execution"):assess(p)
 def test_naive_timestamp_refused(self):
  p=intent();p["asOf"]="2026-10-21T15:00:00"
  with self.assertRaisesRegex(ValueError,"timezone"):assess(p)
if __name__=="__main__":unittest.main()
