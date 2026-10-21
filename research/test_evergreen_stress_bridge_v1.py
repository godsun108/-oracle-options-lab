import unittest
from evergreen_stress_bridge_v1 import evaluate
def export():
 return dict(schema="oracle.evergreen-paper-stress-input.v1",mode="RESEARCH_ONLY",
 ordersEnabled=False,liveOrderAuthorized=False,reportingCurrency="USD",
 brokerFillsVerified=False,portfolioComplete=True,ledgerReconciled=True,
 missingMarks=[],quoteProvenanceVerified=False,stressEligible=False,
 equity=2000,positions=[dict(agentId="SPY::trend_200",riskGroup="SPY",side="LONG",notional=1000)])
def scenarios():
 return [{"id":"equity-down","groupShocks":{"SPY":-.20}}]
class BridgeTests(unittest.TestCase):
 def test_loss_breach_is_warning_never_permission(self):
  r=evaluate(export(),scenarios())
  self.assertTrue(r["stressThresholdBreached"])
  self.assertFalse(r["paperCandidateEligible"])
  self.assertFalse(r["liveOrderAuthorized"])
 def test_nonbreach_still_no_permission(self):
  p=export();p["positions"][0]["notional"]=10
  r=evaluate(p,scenarios())
  self.assertFalse(r["stressThresholdBreached"])
  self.assertFalse(r["sourceEvidenceVerified"])
 def test_incomplete_export_blocks(self):
  p=export();p["portfolioComplete"]=False
  self.assertIsNone(evaluate(p,scenarios())["stress"])
 def test_self_certification_rejected(self):
  p=export();p["quoteProvenanceVerified"]=True
  with self.assertRaisesRegex(ValueError,"self-certified"):evaluate(p,scenarios())
 def test_live_order_flag_rejected(self):
  p=export();p["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"unsafe"):evaluate(p,scenarios())
 def test_unknown_instrument_rejected(self):
  p=export();p["positions"][0]["riskGroup"]="EURUSD"
  with self.assertRaisesRegex(ValueError,"unsupported"):evaluate(p,scenarios())
if __name__=="__main__":unittest.main()
