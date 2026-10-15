import copy
import unittest
from research.challenger_registry import register_candidate, verify_registration

def candidate():
    return dict(candidate_id="SPY-trend-v2", market="SPY", parent_id="SPY-trend-v1",
                code_sha256="a"*64, data_sha256="b"*64,
                registered_at="2026-10-14T20:00:00+00:00",
                evaluation_start="2026-10-16T13:30:00+00:00",
                evaluation_end="2027-01-16T21:00:00+00:00",
                hypothesis="Trend rule with alternative horizon",
                cost_model={"round_trip_bps": 50}, risk_budget={"max_drawdown_pct": 10},
                trial_family_size=20)

class ChallengerRegistryTests(unittest.TestCase):
    def test_registration_is_research_only(self):
        sealed=register_candidate(candidate())
        self.assertTrue(verify_registration(sealed))
        self.assertFalse(sealed["orders_enabled"])
    def test_mutation_invalidates_hash(self):
        sealed=register_candidate(candidate())
        sealed["hypothesis"]="posthoc revision"
        self.assertFalse(verify_registration(sealed))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            register_candidate(candidate(), existing_ids=["SPY-trend-v2"])
    def test_retrospective_registration_rejected(self):
        x=candidate();x["evaluation_start"]=x["registered_at"]
        with self.assertRaises(ValueError):
            register_candidate(x)
    def test_missing_costs_rejected(self):
        x=candidate();x["cost_model"]={}
        with self.assertRaises(ValueError):
            register_candidate(x)
if __name__=="__main__":
    unittest.main()
