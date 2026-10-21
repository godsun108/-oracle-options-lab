import hashlib,unittest
from evergreen_observation_integrity_v1 import verify,canonical
def packet():
 records=[{"id":"a","observedAt":"2026-10-20T14:00:00Z","mid":1.10},
          {"id":"b","observedAt":"2026-10-20T14:01:00Z","mid":1.11}]
 return {"schema":"oracle.forward-observations.v1","mode":"RESEARCH_ONLY",
 "ordersEnabled":False,"observations":records,"sha256":hashlib.sha256(canonical(records)).hexdigest()}
class IntegrityTests(unittest.TestCase):
 def test_valid_digest_is_not_source_proof(self):
  r=verify(packet())
  self.assertTrue(r["structuralIntegrityPassed"])
  self.assertFalse(r["sourceAuthenticityVerified"])
  self.assertFalse(r["paperCandidateEligible"])
 def test_tamper_detected(self):
  p=packet();p["observations"][0]["mid"]=1.2
  self.assertIn("digest_mismatch",verify(p)["reasons"])
 def test_duplicate_id_detected(self):
  p=packet();p["observations"][1]["id"]="a"
  self.assertFalse(verify(p)["structuralIntegrityPassed"])
 def test_out_of_order_detected(self):
  p=packet();p["observations"][1]["observedAt"]="2026-10-19T14:00:00Z"
  self.assertIn("invalid_chronology",verify(p)["reasons"])
 def test_future_observation_detected(self):
  p=packet();p["observations"][1]["observedAt"]="2099-10-20T14:01:00Z"
  self.assertIn("invalid_chronology",verify(p)["reasons"])
 def test_live_flag_rejected(self):
  p=packet();p["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"unsafe"):verify(p)
if __name__=="__main__":unittest.main()
