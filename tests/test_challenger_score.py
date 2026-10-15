import unittest
from research.challenger_registry import register_candidate
from research.challenger_score import score_shadow_league

def reg(cid, market):
    return register_candidate(dict(candidate_id=cid, market=market, parent_id=None,
        code_sha256="a"*64, data_sha256="b"*64,
        registered_at="2026-10-14T00:00:00+00:00",
        evaluation_start="2026-10-16T00:00:00+00:00",
        evaluation_end="2026-11-20T00:00:00+00:00",
        hypothesis="Research candidate", cost_model={"bps": 50},
        risk_budget={"max_drawdown": .1}, trial_family_size=3))
def obs(cid, w, ret):
    return dict(candidate_id=cid, window=w, net_return=ret, evidence_sha256="c"*64)

class ShadowScoreTests(unittest.TestCase):
    def test_missing_window_never_ranked(self):
        result=score_shadow_league([reg("a","SPY"),reg("b","SPY")],
            [obs("a","w1",.02),obs("b","w1",.01),obs("b","w2",.01)],required_windows=["w1","w2"])
        self.assertEqual(result["within_market_descriptive_order"]["SPY"],["b"])
        self.assertIsNone(result["rows"][0]["net_profit_usd"])
    def test_same_market_competition(self):
        result=score_shadow_league([reg("a","SPY"),reg("b","SPY")],
            [obs("a","w1",.03),obs("b","w1",.01)],required_windows=["w1"])
        self.assertEqual(result["within_market_descriptive_order"]["SPY"],["a","b"])
        self.assertFalse(result["promotion_authorized"])
    def test_duplicate_observation_rejected(self):
        with self.assertRaises(ValueError):
            score_shadow_league([reg("a","SPY")],[obs("a","w1",.01),obs("a","w1",.02)],required_windows=["w1"])
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            score_shadow_league([reg("a","SPY")],[obs("a","w1",float("nan"))],required_windows=["w1"])
    def test_invalid_registration_rejected(self):
        r=reg("a","SPY");r["hypothesis"]="changed"
        with self.assertRaises(ValueError):
            score_shadow_league([r],[],required_windows=["w1"])
if __name__=="__main__":
    unittest.main()
