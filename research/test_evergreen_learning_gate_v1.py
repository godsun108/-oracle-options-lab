import unittest
from evergreen_learning_gate_v1 import evaluate
def candidate():
 return dict(mode="RESEARCH_ONLY",ordersEnabled=False,candidateId="challenger-v2",
 baselineId="baseline-v1",evidenceHash="sha256:fixture",forwardSessions=60,
 completedTrades=20,netReturnDifference=0.02,bootstrapLowerBound=0.001,
 maxDrawdown=0.08,baselineMaxDrawdown=0.09,costStressNetReturnDifference=0.01,
 independentLineageVerified=True,forwardOnlyVerified=True,
 allCostsVerified=True,benchmarkVerified=True)
class EvergreenTests(unittest.TestCase):
 def test_eligible_still_never_promotes(self):
  r=evaluate(candidate())
  self.assertTrue(r["reviewEligible"]);self.assertFalse(r["promotionAuthorized"])
  self.assertFalse(r["ordersEnabled"])
 def test_weak_evidence_blocks(self):
  c=candidate();c["forwardSessions"]=59
  r=evaluate(c);self.assertFalse(r["reviewEligible"])
 def test_drawdown_regression_blocks(self):
  c=candidate();c["maxDrawdown"]=0.20
  self.assertFalse(evaluate(c)["reviewEligible"])
 def test_uncertainty_blocks(self):
  c=candidate();c["bootstrapLowerBound"]=-0.01
  self.assertFalse(evaluate(c)["reviewEligible"])
 def test_unverified_lineage_blocks(self):
  c=candidate();c["independentLineageVerified"]=False
  self.assertFalse(evaluate(c)["reviewEligible"])
 def test_live_orders_refused(self):
  c=candidate();c["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"live execution"):evaluate(c)
 def test_nonfinite_metrics_refused(self):
  c=candidate();c["maxDrawdown"]=float("nan")
  with self.assertRaisesRegex(ValueError,"nonfinite"):evaluate(c)
if __name__=="__main__":unittest.main()
