import unittest
from evergreen_unified_paper_gate_v1 import assess
def fixture():
 s=dict(mode="RESEARCH_ONLY",ordersEnabled=False,reconciled=True,quotesVerified=True,
 fxConversionsVerified=True,equity=2000,peakEquity=2000,dayStartEquity=2000,
 grossExposure=100,positions=[dict(riskGroup="SPY",notional=100)])
 p=dict(action="OPEN",notional=50,riskGroup="SPY",verifiedVenueSession=True,
 verifiedQuote=True,independentStrategyEvidence=True)
 m=dict(ordersEnabled=False,killSwitch=False,capitalLimit=2000,maxPositionFraction=.05,
 maxGrossFraction=.5,maxGroupFraction=.1,dailyLossFraction=.01,drawdownFraction=.05)
 e=dict(schema="oracle.evergreen-paper-stress-input.v1",mode="RESEARCH_ONLY",
 ordersEnabled=False,liveOrderAuthorized=False,reportingCurrency="USD",
 brokerFillsVerified=False,portfolioComplete=True,ledgerReconciled=True,
 missingMarks=[],quoteProvenanceVerified=False,stressEligible=False,
 equity=2000,positions=[dict(agentId="SPY::trend_200",riskGroup="SPY",side="LONG",notional=100)])
 scenarios=[dict(id="drop",groupShocks={"SPY":-.1})]
 return s,p,m,e,scenarios
class UnifiedTests(unittest.TestCase):
 def test_nominal_hypothetical_risk_still_no_authorization(self):
  r=assess(*fixture())
  self.assertTrue(r["hypotheticalRiskWithinLimits"])
  self.assertFalse(r["paperCandidateEligible"])
  self.assertFalse(r["liveOrderAuthorized"])
 def test_stress_breach_blocks(self):
  s,p,m,e,sc=fixture();e["positions"][0]["notional"]=1200
  r=assess(s,p,m,e,sc)
  self.assertFalse(r["hypotheticalRiskWithinLimits"])
  self.assertIn("stress:threshold_breached",r["reasons"])
 def test_kill_switch_blocks(self):
  s,p,m,e,sc=fixture();m["killSwitch"]=True
  r=assess(s,p,m,e,sc)
  self.assertFalse(r["hypotheticalRiskWithinLimits"])
 def test_incomplete_stress_blocks(self):
  s,p,m,e,sc=fixture();e["portfolioComplete"]=False
  r=assess(s,p,m,e,sc)
  self.assertIn("stress:incomplete",r["reasons"])
 def test_live_order_request_rejected(self):
  s,p,m,e,sc=fixture();m["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"live execution"):assess(s,p,m,e,sc)
if __name__=="__main__":unittest.main()
