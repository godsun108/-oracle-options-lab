import unittest
from evergreen_portfolio_risk_v1 import assess

def fixtures():
 s=dict(mode="RESEARCH_ONLY",ordersEnabled=False,reconciled=True,quotesVerified=True,
 fxConversionsVerified=True,equity=2000,peakEquity=2000,dayStartEquity=2000,
 grossExposure=100,positions=[dict(riskGroup="USD",notional=100)])
 p=dict(action="OPEN",notional=50,riskGroup="USD",verifiedVenueSession=True,
 verifiedQuote=True,independentStrategyEvidence=True)
 m=dict(ordersEnabled=False,killSwitch=False,capitalLimit=2000,maxPositionFraction=.05,
 maxGrossFraction=.5,maxGroupFraction=.1,dailyLossFraction=.01,drawdownFraction=.05)
 return s,p,m

class GovernorTests(unittest.TestCase):
 def test_eligible_paper_never_live(self):
  s,p,m=fixtures();r=assess(s,p,m)
  self.assertTrue(r["paperCandidateEligible"]);self.assertFalse(r["liveOrderAuthorized"])
 def test_correlation_blocks(self):
  s,p,m=fixtures();p["notional"]=101
  self.assertIn("correlated_group_limit",assess(s,p,m)["reasons"])
 def test_daily_loss_halts(self):
  s,p,m=fixtures();s["equity"]=1979
  self.assertIn("daily_loss_halt",assess(s,p,m)["reasons"])
 def test_drawdown_halts(self):
  s,p,m=fixtures();s["equity"]=1800
  self.assertIn("drawdown_halt",assess(s,p,m)["reasons"])
 def test_kill_switch(self):
  s,p,m=fixtures();m["killSwitch"]=True
  self.assertFalse(assess(s,p,m)["paperCandidateEligible"])
 def test_unverified_snapshot(self):
  s,p,m=fixtures();s["reconciled"]=False
  self.assertFalse(assess(s,p,m)["paperCandidateEligible"])
 def test_exposure_mismatch(self):
  s,p,m=fixtures();s["grossExposure"]=0
  self.assertIn("exposure_reconciliation_failed",assess(s,p,m)["reasons"])
 def test_live_orders_prohibited(self):
  s,p,m=fixtures();m["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"live execution"):assess(s,p,m)
 def test_close_requires_separate_validation(self):
  s,p,m=fixtures();p["action"]="CLOSE"
  self.assertFalse(assess(s,p,m)["paperCandidateEligible"])
if __name__=="__main__":unittest.main()
