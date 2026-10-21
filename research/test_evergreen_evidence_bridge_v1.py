import unittest
from evergreen_evidence_bridge_v1 import evaluate_evidence
def packet():
 return {"schema":"oracle.evergreen-forward-evidence.v1","mode":"RESEARCH_ONLY",
 "ordersEnabled":False,"candidateId":"c2","baselineId":"c1","evidenceHash":"sha256:example",
 "forwardSessions":100,"completedTrades":100,"netReturnDifference":.5,
 "bootstrapLowerBound":.2,"maxDrawdown":.01,"baselineMaxDrawdown":.1,
 "costStressNetReturnDifference":.4}
class BridgeTests(unittest.TestCase):
 def test_unattested_performance_never_promotes(self):
  r=evaluate_evidence(packet())
  self.assertFalse(r["reviewEligible"]);self.assertFalse(r["promotionAuthorized"])
 def test_self_attested_digest_is_not_trusted(self):
  p=packet()
  p["attestations"]={k:{"passed":True,"auditSha256":"a"*64}
    for k in ("lineage","forward","costs","benchmark")}
  r=evaluate_evidence(p)
  self.assertTrue(all(r["attestationsAccepted"].values()))
  self.assertFalse(r["sourceEvidenceVerified"])
  self.assertFalse(r["reviewEligible"])
 def test_missing_metrics_refused(self):
  p=packet();del p["forwardSessions"]
  with self.assertRaises(ValueError):evaluate_evidence(p)
 def test_live_execution_refused(self):
  p=packet();p["ordersEnabled"]=True
  with self.assertRaises(ValueError):evaluate_evidence(p)
 def test_wrong_schema_refused(self):
  p=packet();p["schema"]="unknown"
  with self.assertRaises(ValueError):evaluate_evidence(p)
if __name__=="__main__":unittest.main()
