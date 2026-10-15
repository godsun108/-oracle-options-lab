import unittest
from research.challenger_registry import register_candidate
from research.challenger_promotion import evaluate_promotion

def fixtures():
    registration=register_candidate(dict(candidate_id="SPY-v2",market="SPY",parent_id="SPY-v1",
        code_sha256="a"*64,data_sha256="b"*64,
        registered_at="2026-10-14T00:00:00+00:00",
        evaluation_start="2026-10-16T00:00:00+00:00",
        evaluation_end="2027-01-16T00:00:00+00:00",
        hypothesis="new version",cost_model={"bps":50},risk_budget={"drawdown":.1},trial_family_size=20))
    return (dict(registration=registration,status="COMPLETE_DESCRIPTIVE",net_return_pct=12),
            dict(candidate_id="SPY-v1",market="SPY",status="COMPLETE_DESCRIPTIVE",net_return_pct=8))
def decide(**kw):
    c,i=fixtures()
    args=dict(independent_audit_passed=True,prospective_windows=30,holdout_untouched=True,
              multiple_testing_control_passed=True,risk_limits_passed=True)
    args.update(kw)
    return evaluate_promotion(c,i,**args)

class PromotionTests(unittest.TestCase):
    def test_success_is_recommendation_not_authorization(self):
        r=decide()
        self.assertEqual(r["decision"],"RECOMMEND_NEXT_PAPER_SEASON")
        self.assertFalse(r["paper_promotion_authorized"])
        self.assertFalse(r["live_promotion_authorized"])
    def test_no_audit_no_promotion(self):
        self.assertEqual(decide(independent_audit_passed=False)["decision"],"DO_NOT_PROMOTE")
    def test_no_multiple_testing_control(self):
        self.assertEqual(decide(multiple_testing_control_passed=False)["decision"],"DO_NOT_PROMOTE")
    def test_short_forward_window(self):
        self.assertEqual(decide(prospective_windows=2)["decision"],"DO_NOT_PROMOTE")
    def test_no_improvement(self):
        c,i=fixtures();c["net_return_pct"]=7
        r=evaluate_promotion(c,i,independent_audit_passed=True,prospective_windows=30,
             holdout_untouched=True,multiple_testing_control_passed=True,risk_limits_passed=True)
        self.assertEqual(r["decision"],"DO_NOT_PROMOTE")
    def test_tampered_registration_rejected(self):
        c,i=fixtures();c["registration"]["hypothesis"]="changed"
        with self.assertRaises(ValueError):
            evaluate_promotion(c,i,independent_audit_passed=True,prospective_windows=30,
                 holdout_untouched=True,multiple_testing_control_passed=True,risk_limits_passed=True)
if __name__=="__main__":
    unittest.main()
