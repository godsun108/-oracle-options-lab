import unittest
from research.paco_oracle_pipeline import observe

NOW="2026-10-09T09:30:00-04:00"
class PipelineTests(unittest.TestCase):
    def test_no_history_is_not_a_trade(self):
        x=observe(spx_bars=[],spy_contracts=[],option_quotes=[],positions=[],now_iso=NOW)
        self.assertEqual(x["put_signal"]["status"],"INSUFFICIENT_HISTORY")
        self.assertEqual(x["paper_fills"],[])
        self.assertFalse(x["orders_enabled"])
        self.assertFalse(x["strategy_performance_available"])
    def test_regime_prioritizes_both_directions(self):
        base={"bid":1.30,"ask":1.35,"reference_mid":2.40,"quote_age_seconds":0.1,
              "ask_size":5,"age_seconds":0.1,"bid_size":5}
        quotes=[dict(base,symbol="PUT",type="put",dte=45),
                dict(base,symbol="CALL",type="call",dte=35)]
        x=observe(spx_bars=[],spy_contracts=[],option_quotes=quotes,positions=[],
                  now_iso=NOW,regime="LOW")
        self.assertEqual([a["type"] for a in x["bargain_candidates"]],["call","put"])
        self.assertEqual(x["executed_trades"],[])
    def test_invalid_regime_rejected(self):
        with self.assertRaises(ValueError):
            observe(spx_bars=[],spy_contracts=[],option_quotes=[],positions=[],
                    now_iso=NOW,regime="GUESS")
if __name__=="__main__":unittest.main()
