import hashlib,unittest
from datetime import datetime,timezone
from evergreen_observation_integrity_v1 import canonical
from evergreen_reproducible_pipeline_v1 import evaluate
def fixture():
 records=[dict(id="a",observedAt="2026-10-20T14:00:00Z",mid=100)]
 o=dict(schema="oracle.forward-observations.v1",mode="RESEARCH_ONLY",ordersEnabled=False,
 observations=records,sha256=hashlib.sha256(canonical(records)).hexdigest())
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
 return o,s,p,m,e,[dict(id="shock",groupShocks={"SPY":-.1})]
class PipelineTests(unittest.TestCase):
 def test_reproducible_without_authorization(self):
  a=evaluate(*fixture());b=evaluate(*fixture())
  self.assertEqual(a,b)
  self.assertTrue(a["structuralIntegrityPassed"])
  self.assertFalse(a["paperCandidateEligible"])
 def test_tampered_observation_stays_blocked(self):
  f=list(fixture());f[0]["observations"][0]["mid"]=200
  r=evaluate(*f)
  self.assertFalse(r["structuralIntegrityPassed"])
  self.assertIn("digest_mismatch",r["reasons"])
 def test_stress_breach_stays_blocked(self):
  f=list(fixture());f[4]["positions"][0]["notional"]=1500
  r=evaluate(*f)
  self.assertTrue(r["unifiedRisk"]["stress"]["stressThresholdBreached"])
  self.assertFalse(r["paperCandidateEligible"])
 def test_kill_switch_stays_blocked(self):
  f=list(fixture());f[3]["killSwitch"]=True
  self.assertFalse(evaluate(*f)["unifiedRisk"]["hypotheticalRiskWithinLimits"])
 def test_live_mode_refused(self):
  f=list(fixture());f[0]["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"unsafe"):evaluate(*f)
if __name__=="__main__":unittest.main()
