import unittest
from edge_profitability_scorecard_v1 import score

def trades(pnls):
    result=[];equity=2000.
    for i,pnl in enumerate(pnls):
        result.append({"id":str(i),"status":"SETTLED_PAPER","broker_fill_verified":False,
                       "gross_pnl":float(pnl)+1,"total_cost":1.,"starting_equity":equity})
        equity+=pnl
    return result

class ScorecardTests(unittest.TestCase):
    def test_empty_no_trade(self):
        self.assertFalse(score([])["preliminary_edge_gate_passed"])
    def test_small_winner_not_enough(self):
        self.assertFalse(score(trades([10]*5))["preliminary_edge_gate_passed"])
    def test_costs_count(self):
        a=trades([-0.5]*30)
        self.assertLess(score(a)["net_expectancy_per_trade"],0)
        self.assertAlmostEqual(a[0]["gross_pnl"]-a[0]["total_cost"],-0.5)
    def test_loss_streak_fails(self):
        self.assertFalse(score(trades([-5]*30))["preliminary_edge_gate_passed"])
    def test_profitable_sample_is_still_not_promotion(self):
        a=score(trades([2]*30))
        self.assertTrue(a["preliminary_edge_gate_passed"])
        self.assertFalse(a["promotion_authorized"])
    def test_rejects_discontinuous_equity(self):
        a=trades([1,1]);a[1]["starting_equity"]=2000
        with self.assertRaisesRegex(ValueError,"discontinuity"):score(a)
    def test_rejects_real_fill_claim(self):
        a=trades([1]);a[0]["broker_fill_verified"]=True
        with self.assertRaisesRegex(ValueError,"settled simulated"):score(a)

if __name__=="__main__":unittest.main()
